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

from regulahub.db.models import System, SystemEndpoint
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


async def _enrich_with_cadsus(
    rows: list[ScheduleExportRow],
    progress: ExecutionProgress,
) -> list[EnrichedAppointment]:
    """Enrich export rows with CADSUS patient data (CPF, phone, email, mother/father names).

    Uses the same CADSUS client as the agendamentos page enrichment.
    """
    if not rows:
        return []

    progress.stage = "enriching"

    from regulahub.config import get_cadsus_settings
    from regulahub.integrations.cadsus_client import CadsusClient

    settings = get_cadsus_settings()
    cadsus_results: dict[str, dict] = {}

    # Extract unique CNS
    unique_cns = list({row.cns for row in rows if row.cns})

    if unique_cns and settings.cadsus_enabled:
        cadsus = CadsusClient(settings=settings)
        semaphore = asyncio.Semaphore(40)

        async def _lookup(cns: str) -> None:
            async with semaphore:
                patient = await cadsus.get_patient_by_cns(cns)
                if patient and patient.cpf:
                    cadsus_results[cns] = {
                        "cpf": patient.cpf or "",
                        "phone": patient.phone or "",
                        "email": patient.email or "",
                        "mother_name": patient.mother_name or "",
                        "father_name": patient.father_name or "",
                    }

        logger.info("Worker CADSUS enrichment: %d unique CNS", len(unique_cns))
        await asyncio.gather(*[_lookup(cns) for cns in unique_cns])
        logger.info("Worker CADSUS: %d/%d enriched", len(cadsus_results), len(unique_cns))

    # Build enriched appointments from export rows + CADSUS data
    enriched: list[EnrichedAppointment] = []
    for row in rows:
        cadsus = cadsus_results.get(row.cns, {})
        enriched.append(
            EnrichedAppointment(
                code=row.solicitacao,
                patient_cns=row.cns,
                patient_name=row.nome,
                patient_cpf=cadsus.get("cpf", ""),
                patient_birth_date=row.dt_nascimento,
                patient_mother_name=cadsus.get("mother_name", row.nome_mae),
                patient_phone=cadsus.get("phone", row.telefone),
                patient_phone_ddd="",
                doctor_name=row.nome_profissional_executante,
                appointment_date=f"{row.data_agendamento} {row.hr_agendamento}".strip(),
                procedure=row.descricao_procedimento,
                department=row.unidade_fantasia,
                department_solicitation=row.mun_solicitante,
                confirmation_key="",
                status=row.situacao,
            )
        )

    progress.total_enriched = len(cadsus_results)
    return enriched


async def _push_to_integration(
    enriched: list[EnrichedAppointment],
    system: System,
    endpoints: list[SystemEndpoint],
    api_key: str | None,
    progress: ExecutionProgress,
) -> BatchPushResult:
    """Push enriched appointments to the integration system."""
    progress.stage = "pushing"
    batch_result = BatchPushResult(total=len(enriched))

    async with IntegrationPushClient(system, endpoints, api_key=api_key) as client:
        for appointment in enriched:
            if progress.cancelled:
                break
            result = await client.process_appointment(appointment.to_dict())
            batch_result.results.append(result)
            if result.success:
                batch_result.pushed += 1
                progress.total_pushed = batch_result.pushed
            else:
                batch_result.failed += 1
                progress.total_failed = batch_result.failed

    return batch_result


async def _resolve_integration_system(
    db_session: AsyncSession,
    system_code: str,
) -> tuple[System, list[SystemEndpoint]]:
    """Resolve integration system and its endpoints from DB."""
    repo = RegulationSystemRepository(db_session)
    system = await repo.get_by_code(system_code)
    if not system:
        raise RuntimeError(f"Integration system '{system_code}' not found")

    endpoints = await repo.get_endpoints_for_system(system.id)
    if not endpoints:
        raise RuntimeError(f"No endpoints configured for system '{system_code}'")

    return system, endpoints


async def _resolve_integration_api_key(
    db_session: AsyncSession,
    system_code: str,
) -> str | None:
    """Resolve API key for the integration system from credentials."""
    repo = CredentialRepository(db_session)
    creds = await repo.get_active_by_system_and_profile(system_code, "API_CLIENT")
    if creds:
        try:
            return decrypt_password(creds[0].encrypted_password)
        except ValueError:
            logger.warning("Failed to decrypt integration API key for %s", system_code)
    return None


async def execute_integration(
    execution_id: uuid.UUID,
    system_code: str,
    date_from: date,
    date_to: date,
) -> None:
    """Main worker pipeline — runs as a background task with its own DB session.

    Pipeline: resolve credentials → export schedules → filter teleconsulta → enrich CADSUS → push.
    """
    from regulahub.db.engine import get_session_factory

    progress = ExecutionProgress(
        execution_id=execution_id,
        date_from=date_from,
        date_to=date_to,
        started_at=datetime.now(UTC),
    )
    _active_executions[execution_id] = progress

    session_factory = get_session_factory()

    try:
        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            progress.status = "running"
            await repo.update_status(
                execution_id,
                "running",
                started_at=progress.started_at,
                progress_data=progress.to_dict(),
            )
            await db_session.commit()

            # Step 1: Resolve credentials and integration system
            credentials = await _resolve_credentials(db_session)
            system, endpoints = await _resolve_integration_system(db_session, system_code)
            api_key = await _resolve_integration_api_key(db_session, system_code)

        if progress.cancelled:
            raise asyncio.CancelledError

        # Step 2: Fetch teleconsulta appointments via schedule export
        rows = await _fetch_appointments(credentials, date_from, date_to, progress)

        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_progress(execution_id, progress.to_dict())
            await db_session.commit()

        if progress.cancelled:
            raise asyncio.CancelledError

        # Step 3: Enrich with CADSUS
        enriched = await _enrich_with_cadsus(rows, progress)

        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_progress(execution_id, progress.to_dict())
            await db_session.commit()

        if progress.cancelled:
            raise asyncio.CancelledError

        # Step 4: Push to integration system
        batch_result = await _push_to_integration(enriched, system, endpoints, api_key, progress)

        # Step 5: Complete
        progress.status = "completed"
        progress.stage = "complete"
        progress.completed_at = datetime.now(UTC)

        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_status(
                execution_id,
                "completed",
                total_fetched=progress.total_fetched,
                total_enriched=progress.total_enriched,
                total_pushed=batch_result.pushed,
                total_failed=batch_result.failed,
                progress_data=progress.to_dict(),
                completed_at=progress.completed_at,
            )
            await db_session.commit()

        logger.info(
            "Worker execution %s completed: fetched=%d, enriched=%d, pushed=%d, failed=%d",
            execution_id,
            progress.total_fetched,
            progress.total_enriched,
            batch_result.pushed,
            batch_result.failed,
        )

    except asyncio.CancelledError:
        progress.status = "cancelled"
        progress.completed_at = datetime.now(UTC)
        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_status(
                execution_id,
                "cancelled",
                total_fetched=progress.total_fetched,
                total_enriched=progress.total_enriched,
                total_pushed=progress.total_pushed,
                total_failed=progress.total_failed,
                progress_data=progress.to_dict(),
                completed_at=progress.completed_at,
            )
            await db_session.commit()
        logger.info("Worker execution %s cancelled", execution_id)

    except Exception as exc:
        progress.status = "failed"
        progress.error_message = str(exc)
        progress.completed_at = datetime.now(UTC)
        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_status(
                execution_id,
                "failed",
                error_message=str(exc),
                total_fetched=progress.total_fetched,
                total_enriched=progress.total_enriched,
                total_pushed=progress.total_pushed,
                total_failed=progress.total_failed,
                progress_data=progress.to_dict(),
                completed_at=progress.completed_at,
            )
            await db_session.commit()
        logger.exception("Worker execution %s failed", execution_id)


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
