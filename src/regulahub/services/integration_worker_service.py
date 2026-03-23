"""Integration worker service — fetches SisReg appointments and pushes to integration systems.

Pipeline: export schedules (same as agendamentos page) → filter teleconsulta → enrich (CADSUS) → push.
Runs as an in-process async task triggered by the API. Status tracked in-memory + persisted to DB.
"""

import asyncio
import dataclasses
import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.repositories.credential import CredentialRepository
from regulahub.db.repositories.integration_execution import IntegrationExecutionRepository
from regulahub.db.repositories.regulation_system import RegulationSystemRepository
from regulahub.services.integration_push_client import BatchPushResult, IntegrationPushClient
from regulahub.sisreg.client import SisregClient, SisregLoginError
from regulahub.sisreg.export_parser import parse_export_csv
from regulahub.sisreg.models import ScheduleExportRow
from regulahub.utils.encryption import decrypt_password
from regulahub.utils.masking import mask_username

logger = logging.getLogger(__name__)

SISREG_BASE_URL = "https://sisregiii.saude.gov.br"
TELECONSULTA_FILTER = "TELECONSULTA"


@dataclasses.dataclass
class ExecutionProgress:
    """In-memory execution progress for real-time polling."""

    execution_id: uuid.UUID
    date_from: date | None = None
    date_to: date | None = None
    status: str = "pending"
    stage: str = "initializing"
    total_fetched: int = 0
    total_enriched: int = 0
    total_pushed: int = 0
    total_failed: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled: bool = False

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "fetchedCount": self.total_fetched,
            "enrichedCount": self.total_enriched,
            "pushedCount": self.total_pushed,
            "failedCount": self.total_failed,
        }


# Module-level in-memory store for active execution progress
_active_executions: dict[uuid.UUID, ExecutionProgress] = {}


def get_execution_progress(execution_id: uuid.UUID) -> ExecutionProgress | None:
    """Get in-memory progress for an active execution."""
    return _active_executions.get(execution_id)


@dataclasses.dataclass
class EnrichedAppointment:
    """Enriched appointment data ready for integration push."""

    code: str
    patient_cns: str = ""
    patient_name: str = ""
    patient_cpf: str = ""
    patient_birth_date: str = ""
    patient_mother_name: str = ""
    patient_phone: str = ""
    patient_phone_ddd: str = ""
    doctor_name: str = ""
    appointment_date: str = ""
    procedure: str = ""
    department: str = ""
    department_solicitation: str = ""
    confirmation_key: str = ""
    status: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


async def _resolve_credentials(
    db_session: AsyncSession,
    profile_type: str = "EXECUTANTE/SOLICITANTE",
) -> list[tuple[str, str]]:
    """Resolve all active credentials for the given profile type."""
    repo = CredentialRepository(db_session)
    creds = await repo.get_active_by_system_and_profile("SISREG", profile_type)

    if not creds:
        raise RuntimeError(f"No {profile_type} credentials configured for SISREG")

    resolved: list[tuple[str, str]] = []
    for cred in creds:
        try:
            pw = decrypt_password(cred.encrypted_password)
            resolved.append((cred.username, pw))
        except ValueError:
            logger.warning("Failed to decrypt credential for operator %s", mask_username(cred.username))

    if not resolved:
        raise RuntimeError(f"All {profile_type} credentials failed decryption")

    return resolved


async def _fetch_appointments(
    credentials: list[tuple[str, str]],
    date_from: date,
    date_to: date,
    progress: ExecutionProgress,
) -> list[ScheduleExportRow]:
    """Fetch teleconsulta appointments using SisReg schedule export (same as agendamentos page).

    Uses export_schedule() with all operators in parallel, deduplicates by solicitacao,
    and filters by teleconsulta procedure.
    """
    progress.stage = "fetching"

    date_from_br = date_from.strftime("%d/%m/%Y")
    date_to_br = date_to.strftime("%d/%m/%Y")
    semaphore = asyncio.Semaphore(5)

    async def _export_single(username: str, password: str) -> list[ScheduleExportRow]:
        user_hash = mask_username(username)
        async with semaphore:
            try:
                async with SisregClient(SISREG_BASE_URL, username, password, "EXECUTANTE/SOLICITANTE") as client:
                    raw_bytes = await client.export_schedule(date_from_br, date_to_br)
                    rows = parse_export_csv(raw_bytes)
                    logger.info("Worker export: operator %s returned %d rows", user_hash, len(rows))
                    return rows
            except SisregLoginError:
                logger.warning("Worker export login failed for operator %s", user_hash)
                return []
            except Exception:
                logger.exception("Worker export error for operator %s", user_hash)
                return []

    # Parallel export across all operators
    tasks = [_export_single(u, p) for u, p in credentials]
    results = await asyncio.gather(*tasks)

    # Merge, deduplicate by solicitacao, and filter teleconsulta
    seen: set[str] = set()
    merged: list[ScheduleExportRow] = []
    for operator_rows in results:
        for row in operator_rows:
            if not row.solicitacao or row.solicitacao in seen:
                continue
            # Filter: only teleconsulta procedures
            if TELECONSULTA_FILTER not in row.descricao_procedimento.upper():
                continue
            seen.add(row.solicitacao)
            merged.append(row)

    progress.total_fetched = len(merged)
    logger.info(
        "Worker fetch: %d teleconsulta appointments from %d operators for %s to %s",
        len(merged), len(credentials), date_from, date_to,
    )
    return merged


async def _enrich_appointments(
    rows: list[ScheduleExportRow],
    credentials: list[tuple[str, str]],
    departments: dict[str, object],
    procedures: dict[str, object],
    execution_mappings: dict[str, object],
    progress: ExecutionProgress,
) -> list[dict]:
    """Enrich export rows: CADSUS (CPF/phone) + SisReg detail (confirmationKey) + mapping resolution.

    Returns list of dicts ready for IntegrationPushClient.process_appointment().
    """
    if not rows:
        return []

    progress.stage = "enriching"

    # ── CADSUS enrichment (parallel) ──
    from regulahub.config import get_cadsus_settings
    from regulahub.integrations.cadsus_client import CadsusClient

    settings = get_cadsus_settings()
    cadsus_results: dict[str, dict] = {}
    unique_cns = list({row.cns for row in rows if row.cns})

    if unique_cns and settings.cadsus_enabled:
        cadsus_client = CadsusClient(settings=settings)
        semaphore = asyncio.Semaphore(40)

        async def _lookup(cns: str) -> None:
            async with semaphore:
                patient = await cadsus_client.get_patient_by_cns(cns)
                if patient and patient.cpf:
                    cadsus_results[cns] = {
                        "cpf": patient.cpf or "",
                        "phone": patient.phone or "",
                        "mother_name": patient.mother_name or "",
                        "birth_date": patient.birth_date or "",
                    }

        logger.info("Worker CADSUS: %d unique CNS", len(unique_cns))
        await asyncio.gather(*[_lookup(cns) for cns in unique_cns])
        logger.info("Worker CADSUS: %d/%d enriched", len(cadsus_results), len(unique_cns))

    # ── SisReg detail for confirmationKey (sequential, single session) ──
    detail_results: dict[str, str] = {}  # solicitacao → confirmationKey
    codes = [row.solicitacao for row in rows if row.solicitacao]

    if codes and credentials:
        username, password = credentials[0]
        user_hash = mask_username(username)
        try:
            async with SisregClient(SISREG_BASE_URL, username, password, "EXECUTANTE/SOLICITANTE") as client:
                for code in codes:
                    try:
                        detail = await client.detail(code)
                        if detail and detail.confirmation_key:
                            detail_results[code] = detail.confirmation_key
                    except Exception:
                        logger.warning("Worker detail failed for code %s", code)
        except SisregLoginError:
            logger.warning("Worker detail login failed for %s", user_hash)
        except Exception:
            logger.exception("Worker detail session failed for %s", user_hash)

        logger.info("Worker detail: %d/%d got confirmationKey", len(detail_results), len(codes))

    # ── Build enriched appointment dicts with resolved mappings ──
    from zoneinfo import ZoneInfo

    manaus_tz = ZoneInfo("America/Manaus")
    enriched: list[dict] = []

    for row in rows:
        cadsus = cadsus_results.get(row.cns, {})
        confirmation_key = detail_results.get(row.solicitacao, "")

        # Resolve procedure by name
        proc = procedures.get(row.descricao_procedimento.upper().strip())
        if not proc:
            logger.warning("Procedure not mapped: %s (code %s)", row.descricao_procedimento, row.solicitacao)
            continue

        # Resolve department by name (unidade_fantasia from CSV)
        dept = departments.get(row.unidade_fantasia.upper().strip())

        # Resolve group_id and location
        group_id = ""
        location = ""
        is_remote = True  # Default to ONLINE for unmapped departments

        if dept:
            group_id = str(dept.group_id)
            is_remote = dept.is_remote
            location = row.unidade_fantasia

            # For PARTIALINTEGRATION, resolve via execution_mapping by requester CNES
            if dept.department_type == "PARTIALINTEGRATION" and row.cnes_solicitante:
                mapping = execution_mappings.get(row.cnes_solicitante)
                if mapping:
                    group_id = str(mapping.group_id)
                    location = mapping.executor_address or row.unidade_fantasia
                    is_remote = True  # PARTIALINTEGRATION = remote
        else:
            # Department not in our mapping — try execution_mapping by requester CNES
            mapping = execution_mappings.get(row.cnes_solicitante) if row.cnes_solicitante else None
            if mapping:
                group_id = str(mapping.group_id)
                location = mapping.executor_address or row.unidade_fantasia
            else:
                # Fallback: use AMBULATORIO VIRTUAL DO AMAZONAS (ONLINE teleconsultation)
                # TODO: refactor — This fallback is Saude AM Digital specific
                fallback_dept = departments.get("AMBULATORIO VIRTUAL DO AMAZONAS")
                if fallback_dept:
                    group_id = str(fallback_dept.group_id)
                    location = row.unidade_fantasia
                    is_remote = True
                else:
                    logger.warning("Department not mapped: %s (code %s)", row.unidade_fantasia, row.solicitacao)
                    continue

        if not group_id:
            logger.warning("No group_id for code %s", row.solicitacao)
            continue

        # Parse appointment date/time → ISO 8601 Manaus timezone
        start_date_str = ""
        end_date_str = ""
        try:
            from datetime import datetime as dt_cls

            date_str = row.data_agendamento.replace(".", "/")  # SisReg uses dots sometimes
            time_str = row.hr_agendamento or "00:00"
            parsed = dt_cls.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
            start_dt = parsed.replace(tzinfo=manaus_tz)
            end_dt = start_dt.replace(minute=start_dt.minute + 30)  # 30-min default slot
            start_date_str = start_dt.isoformat()
            end_date_str = end_dt.isoformat()
        except (ValueError, AttributeError):
            logger.warning("Invalid date for code %s: %s %s", row.solicitacao, row.data_agendamento, row.hr_agendamento)
            continue

        # Split patient name
        name_parts = row.nome.strip().split(" ", 1) if row.nome else ["", ""]
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Birth date: prefer CADSUS, fallback to CSV (ensure dd/MM/yyyy format)
        birth_date = cadsus.get("birth_date", "") or row.dt_nascimento or ""

        # Phone: prefer CADSUS, fallback to CSV, default to 00000000000
        # Clean to digits only, validate 10-15 digits, else fallback
        import re as _re

        raw_phone = cadsus.get("phone", "") or row.telefone or ""
        phone_digits = _re.sub(r"\D", "", raw_phone)
        phone = phone_digits if 10 <= len(phone_digits) <= 15 else "00000000000"

        # Preference of service
        preference = "ONLINE" if is_remote else "PRESENCIAL"

        enriched.append({
            "code": row.solicitacao,
            "external_id": f"{row.solicitacao}-{confirmation_key}" if confirmation_key else row.solicitacao,
            "confirmation_key": confirmation_key,
            "patient_cns": row.cns,
            "patient_cpf": cadsus.get("cpf", ""),
            "patient_first_name": first_name,
            "patient_last_name": last_name,
            "patient_birth_date": birth_date,
            "patient_mother_name": cadsus.get("mother_name", "") or row.nome_mae or "",
            "patient_phone": phone,
            "doctor_name": row.nome_profissional_executante,
            "group_id": group_id,
            "work_scale_name": proc.work_scale_name,
            "preference_of_service": preference,
            "location_of_service": location,
            "start_date": start_date_str,
            "end_date": end_date_str,
        })

    progress.total_enriched = len(cadsus_results)
    logger.info("Worker enrichment complete: %d appointments ready for push", len(enriched))
    return enriched


async def _push_to_integration(
    enriched: list[dict],
    api_key: str,
    progress: ExecutionProgress,
) -> BatchPushResult:
    """Push enriched appointments to the integration system."""
    from regulahub.config import get_integration_settings

    progress.stage = "pushing"
    batch_result = BatchPushResult(total=len(enriched))
    settings = get_integration_settings()

    async with IntegrationPushClient(
        core_api_base_url=settings.integration_core_api_url,
        auth_api_base_url=settings.integration_auth_api_url,
        api_key=api_key,
    ) as client:
        for appointment in enriched:
            if progress.cancelled:
                break
            result = await client.process_appointment(appointment)
            batch_result.results.append(result)
            if result.success:
                batch_result.pushed += 1
                progress.total_pushed = batch_result.pushed
            else:
                batch_result.failed += 1
                progress.total_failed = batch_result.failed
                logger.warning("Push failed for %s: %s", appointment.get("code"), result.error)

    return batch_result


async def execute_integration(
    execution_id: uuid.UUID,
    system_code: str,
    date_from: date,
    date_to: date,
) -> None:
    """Main worker pipeline — runs as a background task with its own DB session.

    Pipeline: resolve credentials → export schedules → filter teleconsulta →
    enrich (CADSUS + detail + mappings) → push to integration system.
    """
    from regulahub.config import get_integration_settings
    from regulahub.db.engine import get_session_factory
    from regulahub.db.repositories.integration_mapping import IntegrationMappingRepository

    progress = ExecutionProgress(
        execution_id=execution_id,
        date_from=date_from,
        date_to=date_to,
        started_at=datetime.now(UTC),
    )
    _active_executions[execution_id] = progress
    session_factory = get_session_factory()

    try:
        # ── Step 0: Resolve credentials, mappings, and API config ──
        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            progress.status = "running"
            await repo.update_status(
                execution_id, "running", started_at=progress.started_at, progress_data=progress.to_dict(),
            )
            await db_session.commit()

            credentials = await _resolve_credentials(db_session)

            # Load all mappings into memory for fast lookup
            mapping_repo = IntegrationMappingRepository(db_session)
            dept_list = await mapping_repo.list_all_departments()
            proc_list = await mapping_repo.list_all_procedures()

            # Build lookup dicts (case-insensitive by uppercase name)
            departments = {d.department_name.upper().strip(): d for d in dept_list}
            procedures = {p.procedure_name.upper().strip(): p for p in proc_list}

            # Execution mappings — load all into dict keyed by requester_cnes
            from regulahub.db.models import IntegrationExecutionMapping  # noqa: I001
            from sqlalchemy import select

            stmt = select(IntegrationExecutionMapping).where(IntegrationExecutionMapping.is_active.is_(True))
            result = await db_session.execute(stmt)
            all_mappings = list(result.scalars().all())
            execution_mappings = {m.requester_cnes: m for m in all_mappings}

        integration_settings = get_integration_settings()
        api_key = integration_settings.integration_api_key
        if not api_key:
            raise RuntimeError("INTEGRATION_API_KEY not configured")

        if progress.cancelled:
            raise asyncio.CancelledError

        # ── Step 1: Fetch teleconsulta appointments ──
        rows = await _fetch_appointments(credentials, date_from, date_to, progress)

        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_progress(execution_id, progress.to_dict())
            await db_session.commit()

        if progress.cancelled:
            raise asyncio.CancelledError

        # ── Step 2: Enrich (CADSUS + detail + mappings) ──
        enriched = await _enrich_appointments(rows, credentials, departments, procedures, execution_mappings, progress)

        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_progress(execution_id, progress.to_dict())
            await db_session.commit()

        if progress.cancelled:
            raise asyncio.CancelledError

        # ── Step 3: Push to integration system ──
        batch_result = await _push_to_integration(enriched, api_key, progress)

        # ── Step 4: Complete ──
        progress.status = "completed"
        progress.stage = "complete"
        progress.completed_at = datetime.now(UTC)

        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_status(
                execution_id, "completed",
                total_fetched=progress.total_fetched, total_enriched=progress.total_enriched,
                total_pushed=batch_result.pushed, total_failed=batch_result.failed,
                progress_data=progress.to_dict(), completed_at=progress.completed_at,
            )
            await db_session.commit()

        logger.info(
            "Worker %s completed: fetched=%d, enriched=%d, pushed=%d, failed=%d",
            execution_id, progress.total_fetched, progress.total_enriched, batch_result.pushed, batch_result.failed,
        )

    except asyncio.CancelledError:
        progress.status = "cancelled"
        progress.completed_at = datetime.now(UTC)
        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_status(
                execution_id, "cancelled",
                total_fetched=progress.total_fetched, total_enriched=progress.total_enriched,
                total_pushed=progress.total_pushed, total_failed=progress.total_failed,
                progress_data=progress.to_dict(), completed_at=progress.completed_at,
            )
            await db_session.commit()
        logger.info("Worker %s cancelled", execution_id)

    except Exception as exc:
        progress.status = "failed"
        progress.error_message = str(exc)
        progress.completed_at = datetime.now(UTC)
        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_status(
                execution_id, "failed", error_message=str(exc),
                total_fetched=progress.total_fetched, total_enriched=progress.total_enriched,
                total_pushed=progress.total_pushed, total_failed=progress.total_failed,
                progress_data=progress.to_dict(), completed_at=progress.completed_at,
            )
            await db_session.commit()
        logger.exception("Worker %s failed", execution_id)


# Store for background tasks so they don't get garbage collected
_background_tasks: dict[uuid.UUID, asyncio.Task] = {}


async def trigger_execution(
    system_code: str,
    date_from: date,
    date_to: date,
    db_session: AsyncSession,
    triggered_by: str = "manual",
) -> uuid.UUID:
    """Trigger a new worker execution. Returns execution ID."""
    system_repo = RegulationSystemRepository(db_session)
    system = await system_repo.get_by_code(system_code)
    if not system:
        raise ValueError(f"Integration system '{system_code}' not found")

    exec_repo = IntegrationExecutionRepository(db_session)
    if await exec_repo.has_running_execution(system.id):
        raise RuntimeError(f"An execution is already running for system '{system_code}'")

    execution_id = uuid.uuid4()
    await exec_repo.create({
        "id": execution_id,
        "integration_system_id": system.id,
        "status": "pending",
        "date_from": date_from,
        "date_to": date_to,
        "triggered_by": triggered_by,
    })
    await db_session.commit()

    task = asyncio.create_task(
        execute_integration(execution_id, system_code, date_from, date_to),
        name=f"integration-worker-{execution_id}",
    )
    _background_tasks[execution_id] = task

    def _cleanup(t: asyncio.Task) -> None:
        _background_tasks.pop(execution_id, None)
        _active_executions.pop(execution_id, None)

    task.add_done_callback(_cleanup)

    return execution_id


def cancel_execution(execution_id: uuid.UUID) -> bool:
    """Request cancellation of a running execution."""
    progress = _active_executions.get(execution_id)
    if progress:
        progress.cancelled = True

    task = _background_tasks.get(execution_id)
    if task and not task.done():
        task.cancel()
        return True
    return False
