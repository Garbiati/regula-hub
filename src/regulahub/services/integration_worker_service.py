"""Integration worker service — fetches SisReg appointments and pushes to integration systems.

Pipeline: export schedules (same as agendamentos page) → filter teleconsulta → enrich (CADSUS) → push.
Runs as an in-process async task triggered by the API. Status tracked in-memory + persisted to DB.
"""

import asyncio
import dataclasses
import logging
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.repositories.credential import CredentialRepository
from regulahub.db.repositories.integration_execution import IntegrationExecutionRepository
from regulahub.db.repositories.regulation_system import RegulationSystemRepository
from regulahub.services.integration_push_client import BatchPushResult, IntegrationPushClient, PushResult
from regulahub.sisreg.client import SisregClient, SisregLoginError
from regulahub.sisreg.export_parser import parse_export_csv
from regulahub.sisreg.models import ScheduleExportRow
from regulahub.utils.encryption import decrypt_password
from regulahub.utils.masking import mask_username

logger = logging.getLogger(__name__)

SISREG_BASE_URL = "https://sisregiii.saude.gov.br"
TELECONSULTA_FILTER = "TELECONSULTA"


def _is_valid_brazilian_phone(digits: str) -> bool:
    """Validate Brazilian phone: 10-11 digits, valid DDD, not all same digit."""
    if len(digits) not in (10, 11):
        return False
    if len(set(digits)) == 1:
        return False
    ddd = int(digits[:2])
    if ddd < 11 or ddd > 99:
        return False
    number_part = digits[2:]
    if len(number_part) == 9 and number_part[0] != "9":
        return False
    return not (len(number_part) == 8 and number_part[0] not in "2345")


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


@dataclasses.dataclass
class EnrichmentResult:
    """Result of the enrichment pipeline — enriched appointments + failures + pending review."""

    enriched: list[dict]
    failed: list[dict]
    needs_review: list[dict] = dataclasses.field(default_factory=list)


def _build_failed_appointment_dict(
    row: ScheduleExportRow,
    cadsus: dict,
    detail: object | None,
    status: str,
    error_message: str,
    error_category: str,
) -> dict:
    """Build a persistence-ready dict for a failed appointment (not pushed, stored with error status)."""
    import re as _re

    confirmation_key = detail.confirmation_key if detail and hasattr(detail, "confirmation_key") else ""

    name_parts = row.nome.strip().split(" ", 1) if row.nome else ["", ""]
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    patient_name = f"{first_name} {last_name}".strip() or "DESCONHECIDO"

    raw_birth = cadsus.get("birth_date", "") or row.dt_nascimento or ""
    birth_date = raw_birth.replace(".", "/").strip() if raw_birth else ""

    raw_phone = cadsus.get("phone", "") or row.telefone or ""
    phone_digits = _re.sub(r"\D", "", raw_phone)
    phone = phone_digits if 10 <= len(phone_digits) <= 15 else ""

    return {
        "regulation_code": row.solicitacao,
        "confirmation_key": confirmation_key or "",
        "external_id": None,
        "patient_name": patient_name,
        "patient_cpf": cadsus.get("cpf", ""),
        "patient_cns": row.cns or "",
        "patient_birth_date": birth_date,
        "patient_phone": phone,
        "patient_mother_name": cadsus.get("mother_name", "") or row.nome_mae or "",
        "procedure_name": row.descricao_procedimento,
        "department_executor": "",
        "department_executor_cnes": "",
        "department_solicitor": row.unidade_fantasia or "",
        "department_solicitor_cnes": row.cnes_solicitante or "",
        "doctor_name": row.nome_profissional_executante or "",
        "status": status,
        "error_message": error_message,
        "error_category": error_category,
        "integration_data": None,
        "source_data": {
            "sisreg_export": {"solicitacao": row.solicitacao, "descricao_procedimento": row.descricao_procedimento},
        },
    }


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
        len(merged),
        len(credentials),
        date_from,
        date_to,
    )
    return merged


async def _enrich_appointments(
    rows: list[ScheduleExportRow],
    credentials: list[tuple[str, str]],
    videofonista_credentials: list[tuple[str, str]],
    departments: dict[str, object],
    departments_by_cnes: dict[str, object],
    procedures: dict[str, object],
    execution_mappings: dict[str, object],
    progress: ExecutionProgress,
) -> EnrichmentResult:
    """Enrich export rows: CADSUS (CPF/phone) + SisReg detail (confirmationKey) + mapping resolution.

    Returns EnrichmentResult with enriched (ready for push) and failed (error persistence).
    """
    if not rows:
        return EnrichmentResult(enriched=[], failed=[])

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

    # ── SisReg detail for confirmationKey + executor department (sequential) ──
    from regulahub.sisreg.models import AppointmentDetail

    detail_results: dict[str, AppointmentDetail] = {}  # solicitacao → full detail
    codes = [row.solicitacao for row in rows if row.solicitacao]

    if codes and videofonista_credentials:
        username, password = videofonista_credentials[0]
        user_hash = mask_username(username)
        try:
            async with SisregClient(SISREG_BASE_URL, username, password, "VIDEOFONISTA") as client:
                for code in codes:
                    try:
                        detail = await client.detail(code)
                        if detail:
                            detail_results[code] = detail
                    except Exception:
                        logger.warning("Worker detail failed for code %s", code)
        except SisregLoginError:
            logger.warning("Worker detail login failed for %s", user_hash)
        except Exception:
            logger.exception("Worker detail session failed for %s", user_hash)

        logger.info("Worker detail: %d/%d fetched", len(detail_results), len(codes))

    # ── Build enriched appointment dicts with resolved mappings ──
    from zoneinfo import ZoneInfo

    manaus_tz = ZoneInfo("America/Manaus")
    enriched: list[dict] = []
    failed: list[dict] = []

    for row in rows:
        cadsus = cadsus_results.get(row.cns, {})
        detail = detail_results.get(row.solicitacao)
        confirmation_key = detail.confirmation_key if detail else ""

        # Resolve procedure by name
        proc = procedures.get(row.descricao_procedimento.upper().strip())
        if not proc:
            logger.warning("Procedure not mapped: %s (code %s)", row.descricao_procedimento, row.solicitacao)
            failed.append(
                _build_failed_appointment_dict(
                    row=row,
                    cadsus=cadsus,
                    detail=detail,
                    status="data_error",
                    error_message=f"Procedure not mapped: {row.descricao_procedimento}",
                    error_category="unmapped_procedure",
                )
            )
            continue

        # ── Resolve group_id using EXECUTOR department (from SisReg detail tbody 3) ──
        # The executor is DYNAMIC per appointment — the same requesting unit can be
        # assigned to different executing units by SisReg regulation.
        # We NEVER infer the executor from static mappings; if the detail page
        # doesn't provide the executor, the appointment MUST fail.
        group_id = ""
        location = ""
        is_remote = True

        executor_name = (detail.exec_unit_name or "").upper().strip() if detail else ""
        executor_cnes = (detail.exec_unit_cnes or "").strip() if detail else ""
        soliciting_cnes = detail.req_unit_cnes or row.cnes_solicitante or "" if detail else row.cnes_solicitante
        soliciting_cnes = soliciting_cnes.strip() if soliciting_cnes else ""

        # If detail didn't provide executor info, fail immediately — don't infer
        if not executor_name and not executor_cnes:
            logger.warning("SisReg detail missing executor unit for code %s", row.solicitacao)
            failed.append(
                _build_failed_appointment_dict(
                    row=row,
                    cadsus=cadsus,
                    detail=detail,
                    status="mapping_error",
                    error_message=f"SisReg detail missing executor unit for code {row.solicitacao}",
                    error_category="missing_detail_executor",
                )
            )
            continue

        # Lookup executor department: by name first, then by CNES as fallback
        executor_dept = departments.get(executor_name) if executor_name else None
        if not executor_dept and executor_cnes:
            executor_dept = departments_by_cnes.get(executor_cnes)

        if executor_dept:
            if executor_dept.department_type == "PARTIALINTEGRATION" and soliciting_cnes:
                # For PARTIALINTEGRATION (e.g., Complexo Regulador), use execution_mapping for routing
                mapping = execution_mappings.get(soliciting_cnes)
                if mapping:
                    group_id = str(mapping.group_id)
                    loc_addr = mapping.executor_address or ""
                    location = f"{mapping.executor_name} - {loc_addr}" if loc_addr else mapping.executor_name
                    is_remote = True
                else:
                    logger.warning(
                        "PARTIALINTEGRATION without execution mapping for code %s (executor=%s, sol_cnes=%s)",
                        row.solicitacao,
                        executor_name,
                        soliciting_cnes,
                    )
                    msg = (
                        f"Interior: no execution mapping for soliciting CNES {soliciting_cnes} ({row.unidade_fantasia})"
                    )
                    failed.append(
                        _build_failed_appointment_dict(
                            row=row,
                            cadsus=cadsus,
                            detail=detail,
                            status="mapping_error",
                            error_message=msg,
                            error_category="missing_execution_mapping",
                        )
                    )
                    continue
            else:
                # FULLINTEGRATION: use the executor department directly
                group_id = str(executor_dept.group_id)
                is_remote = executor_dept.is_remote
                addr = getattr(executor_dept, "department_address", "") or ""
                location = f"{executor_dept.department_name} - {addr}" if addr else executor_dept.department_name
        else:
            # Executor from detail but not found in departments table
            logger.warning(
                "Executor department not found for code %s (name=%s, cnes=%s)",
                row.solicitacao,
                executor_name,
                executor_cnes,
            )
            msg = f"Executor department not in departments table (name='{executor_name}', cnes='{executor_cnes}')"
            failed.append(
                _build_failed_appointment_dict(
                    row=row,
                    cadsus=cadsus,
                    detail=detail,
                    status="mapping_error",
                    error_message=msg,
                    error_category="unmapped_executor_department",
                )
            )
            continue

        if not group_id:
            logger.warning("No group_id for code %s", row.solicitacao)
            failed.append(
                _build_failed_appointment_dict(
                    row=row,
                    cadsus=cadsus,
                    detail=detail,
                    status="mapping_error",
                    error_message=f"Resolved department but group_id is empty for code {row.solicitacao}",
                    error_category="missing_group_id",
                )
            )
            continue

        # Parse appointment date/time → ISO 8601 Manaus timezone
        start_date_str = ""
        end_date_str = ""
        try:
            from datetime import datetime as dt_cls

            date_str = row.data_agendamento.replace(".", "/")  # SisReg uses dots sometimes
            time_str = row.hr_agendamento or "00:00"
            parsed = dt_cls.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
            from datetime import timedelta as td

            start_dt = parsed.replace(tzinfo=manaus_tz)
            end_dt = start_dt + td(minutes=30)  # 30-min default slot
            start_date_str = start_dt.isoformat()
            end_date_str = end_dt.isoformat()
        except (ValueError, AttributeError) as exc:
            logger.warning(
                "Invalid date for code %s: '%s' '%s' — %s",
                row.solicitacao,
                row.data_agendamento,
                row.hr_agendamento,
                exc,
            )
            failed.append(
                _build_failed_appointment_dict(
                    row=row,
                    cadsus=cadsus,
                    detail=detail,
                    status="data_error",
                    error_message=f"Invalid date/time: '{row.data_agendamento}' '{row.hr_agendamento}' — {exc}",
                    error_category="invalid_date",
                )
            )
            continue

        # Split patient name
        name_parts = row.nome.strip().split(" ", 1) if row.nome else ["", ""]
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Birth date: prefer CADSUS, fallback to CSV — normalize to dd/MM/yyyy
        raw_birth = cadsus.get("birth_date", "") or row.dt_nascimento or ""
        birth_date = raw_birth.replace(".", "/").strip() if raw_birth else ""

        # Phone: prefer CADSUS, fallback to CSV, validate semantically
        import re as _re

        raw_phone = cadsus.get("phone", "") or row.telefone or ""
        phone_digits = _re.sub(r"\D", "", raw_phone)
        phone = phone_digits if _is_valid_brazilian_phone(phone_digits) else ""

        # Preference of service
        preference = "ONLINE" if is_remote else "PRESENCIAL"

        enriched.append(
            {
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
                # Extra fields for appointment persistence
                "procedure_name": row.descricao_procedimento,
                "department_executor": executor_dept.department_name if executor_dept else executor_name,
                "department_executor_cnes": executor_dept.cnes_code if executor_dept else executor_cnes,
                "department_solicitor": row.unidade_fantasia,
                "department_solicitor_cnes": row.cnes_solicitante,
            }
        )

    # Separate enriched into ready (valid phone) vs needs_review (missing phone)
    ready_for_push = []
    needs_review = []
    for appt in enriched:
        if not appt.get("patient_phone"):
            needs_review.append(appt)
        else:
            ready_for_push.append(appt)

    progress.total_enriched = len(ready_for_push)
    if needs_review:
        logger.warning(
            "Worker enrichment: %d appointments pending review (missing phone)",
            len(needs_review),
        )
    logger.info(
        "Worker enrichment complete: %d ready for push, %d pending review, %d failed",
        len(ready_for_push),
        len(needs_review),
        len(failed),
    )
    return EnrichmentResult(enriched=ready_for_push, failed=failed, needs_review=needs_review)


async def _persist_appointments(
    enriched: list[dict],
    execution_id: uuid.UUID,
    system_id: uuid.UUID,
    reference_date: date,
    status: str = "pending",
    error_message: str | None = None,
    error_category: str | None = None,
) -> None:
    """Batch insert appointments with given status before push."""
    from regulahub.db.engine import get_session_factory
    from regulahub.db.repositories.integration_appointment import IntegrationAppointmentRepository

    session_factory = get_session_factory()
    async with session_factory() as db_session:
        repo = IntegrationAppointmentRepository(db_session)
        items = []
        for appt in enriched:
            name_parts = [appt.get("patient_first_name", ""), appt.get("patient_last_name", "")]
            patient_name = " ".join(p for p in name_parts if p).strip()

            # Parse appointment_date from start_date ISO string
            appt_date = reference_date
            appt_time = None
            start_str = appt.get("start_date", "")
            if start_str:
                try:
                    from datetime import datetime as dt_cls
                    from datetime import time as time_cls

                    parsed = dt_cls.fromisoformat(start_str)
                    appt_date = parsed.date()
                    appt_time = time_cls(parsed.hour, parsed.minute)
                except (ValueError, AttributeError):
                    pass

            items.append(
                {
                    "integration_system_id": system_id,
                    "execution_id": execution_id,
                    "regulation_code": appt.get("code", ""),
                    "confirmation_key": appt.get("confirmation_key", ""),
                    "external_id": appt.get("external_id", ""),
                    "patient_name": patient_name or "DESCONHECIDO",
                    "patient_cpf": appt.get("patient_cpf", ""),
                    "patient_cns": appt.get("patient_cns", ""),
                    "patient_birth_date": appt.get("patient_birth_date", ""),
                    "patient_phone": appt.get("patient_phone", ""),
                    "patient_mother_name": appt.get("patient_mother_name", ""),
                    "appointment_date": appt_date,
                    "appointment_time": appt_time,
                    "procedure_name": appt.get("procedure_name", "TELECONSULTA"),
                    "department_executor": appt.get("department_executor", ""),
                    "department_executor_cnes": appt.get("department_executor_cnes", ""),
                    "department_solicitor": appt.get("department_solicitor", ""),
                    "department_solicitor_cnes": appt.get("department_solicitor_cnes", ""),
                    "doctor_name": appt.get("doctor_name", ""),
                    "status": status,
                    "error_message": error_message or "",
                    "error_category": error_category or "",
                    "integration_data": {
                        "group_id": appt.get("group_id", ""),
                        "work_scale_name": appt.get("work_scale_name", ""),
                        "preference_of_service": appt.get("preference_of_service", ""),
                        "location_of_service": appt.get("location_of_service", ""),
                    },
                    "source_data": {
                        "sisreg_export": {
                            "solicitacao": appt.get("code", ""),
                            "descricao_procedimento": appt.get("procedure_name", ""),
                        },
                    },
                    "reference_date": reference_date,
                }
            )

        if items:
            await repo.bulk_upsert(items)
            await db_session.commit()
            logger.info("Persisted %d appointments as '%s'", len(items), status)


async def _persist_failed_appointments(
    failed: list[dict],
    execution_id: uuid.UUID,
    system_id: uuid.UUID,
    reference_date: date,
) -> None:
    """Batch upsert failed enrichment appointments (mapping_error/data_error) for operator visibility."""
    if not failed:
        return

    from regulahub.db.engine import get_session_factory
    from regulahub.db.repositories.integration_appointment import IntegrationAppointmentRepository

    session_factory = get_session_factory()
    async with session_factory() as db_session:
        repo = IntegrationAppointmentRepository(db_session)
        items = []
        for appt in failed:
            # Parse date from CSV row data if possible
            appt_date = reference_date
            appt_time = None

            items.append(
                {
                    "integration_system_id": system_id,
                    "execution_id": execution_id,
                    "regulation_code": appt.get("regulation_code", ""),
                    "confirmation_key": appt.get("confirmation_key", ""),
                    "external_id": None,
                    "patient_name": appt.get("patient_name", "DESCONHECIDO"),
                    "patient_cpf": appt.get("patient_cpf", ""),
                    "patient_cns": appt.get("patient_cns", ""),
                    "patient_birth_date": appt.get("patient_birth_date", ""),
                    "patient_phone": appt.get("patient_phone", ""),
                    "patient_mother_name": appt.get("patient_mother_name", ""),
                    "appointment_date": appt_date,
                    "appointment_time": appt_time,
                    "procedure_name": appt.get("procedure_name", ""),
                    "department_executor": appt.get("department_executor", ""),
                    "department_executor_cnes": appt.get("department_executor_cnes", ""),
                    "department_solicitor": appt.get("department_solicitor", ""),
                    "department_solicitor_cnes": appt.get("department_solicitor_cnes", ""),
                    "doctor_name": appt.get("doctor_name", ""),
                    "status": appt.get("status", "data_error"),
                    "error_message": appt.get("error_message", ""),
                    "error_category": appt.get("error_category", ""),
                    "integration_data": appt.get("integration_data"),
                    "source_data": appt.get("source_data"),
                    "reference_date": reference_date,
                }
            )

        if items:
            await repo.bulk_upsert(items)
            await db_session.commit()
            logger.info("Persisted %d failed appointments (mapping/data errors)", len(items))


async def _update_appointment_status(
    regulation_code: str,
    status: str,
    push_result: PushResult,
    integration_data_update: dict | None = None,
) -> None:
    """Update a single appointment after push result.

    MERGES integration_data instead of replacing, so persisted fields
    (group_id, location_of_service, preference_of_service) are preserved.
    """
    from regulahub.db.engine import get_session_factory
    from regulahub.db.repositories.integration_appointment import IntegrationAppointmentRepository

    session_factory = get_session_factory()
    async with session_factory() as db_session:
        repo = IntegrationAppointmentRepository(db_session)
        appt = await repo.get_by_regulation_code(regulation_code)
        if not appt:
            return
        # Merge push result into existing integration_data (preserve group_id, location, etc.)
        merged_data = dict(appt.integration_data or {})
        if integration_data_update:
            merged_data.update(integration_data_update)
        await repo.update_status(
            appt.id,
            status=status,
            error_message=push_result.error,
            error_category=push_result.error_category or None,
            integration_data=merged_data,
        )
        await db_session.commit()


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

            # Update appointment record with result
            if result.success:
                batch_result.pushed += 1
                progress.total_pushed = batch_result.pushed
                status = "skipped" if result.appointment_skipped else "integrated"
                int_data = {
                    "patient_id": result.patient_id,
                    "appointment_id": result.appointment_id,
                    "is_new_account": result.is_new_account,
                }
                await _update_appointment_status(result.code, status, result, int_data)
            else:
                batch_result.failed += 1
                progress.total_failed = batch_result.failed
                status = f"{result.error_category}_error" if result.error_category else "appointment_error"
                await _update_appointment_status(result.code, status, result)
                logger.warning("Push failed for %s: %s", result.code, result.error)

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
                execution_id,
                "running",
                started_at=progress.started_at,
                progress_data=progress.to_dict(),
            )
            await db_session.commit()

            credentials = await _resolve_credentials(db_session)
            videofonista_creds = await _resolve_credentials(db_session, "VIDEOFONISTA")

            # Resolve system ID for appointment persistence
            from regulahub.db.repositories.regulation_system import RegulationSystemRepository

            sys_repo = RegulationSystemRepository(db_session)
            system = await sys_repo.get_by_code(system_code)
            system_id = system.id if system else None

            # Load all mappings into memory for fast lookup
            mapping_repo = IntegrationMappingRepository(db_session)
            dept_list = await mapping_repo.list_all_departments()
            proc_list = await mapping_repo.list_all_procedures()

            # Build lookup dicts (case-insensitive by uppercase name, and by CNES)
            departments = {d.department_name.upper().strip(): d for d in dept_list}
            departments_by_cnes = {d.cnes_code.strip(): d for d in dept_list if d.cnes_code}
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
        enrich_result = await _enrich_appointments(
            rows,
            credentials,
            videofonista_creds,
            departments,
            departments_by_cnes,
            procedures,
            execution_mappings,
            progress,
        )
        enriched = enrich_result.enriched

        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_progress(execution_id, progress.to_dict())
            await db_session.commit()

        if progress.cancelled:
            raise asyncio.CancelledError

        # ── Step 2.5: Persist appointments as 'pending' before push ──
        if enriched and system_id:
            await _persist_appointments(enriched, execution_id, system_id, date_from)

        # ── Step 2.5b: Persist appointments needing review (missing required fields) ──
        if enrich_result.needs_review and system_id:
            await _persist_appointments(
                enrich_result.needs_review,
                execution_id,
                system_id,
                date_from,
                status="pending_review",
                error_message="Telefone do paciente ausente ou invalido (CADSUS/CSV)",
                error_category="missing_phone",
            )
            from regulahub.services.slack_notifier import send_slack_alert

            names = [a.get("patient_first_name", "?") for a in enrich_result.needs_review[:10]]
            await send_slack_alert(
                f"Agendamentos pendentes de revisao: {len(enrich_result.needs_review)} sem telefone valido",
                context={
                    "Motivo": "Telefone nao encontrado no CADSUS nem no CSV do SISReg",
                    "Pacientes": ", ".join(names) + ("..." if len(enrich_result.needs_review) > 10 else ""),
                    "Acao": "Verificar dados no CADSUS ou corrigir manualmente",
                },
            )

        # ── Step 2.6: Persist failed appointments (mapping/data errors) for operator visibility ──
        if enrich_result.failed and system_id:
            await _persist_failed_appointments(enrich_result.failed, execution_id, system_id, date_from)

        # ── Step 3: Push to integration system (only enriched, not failed) ──
        batch_result = await _push_to_integration(enriched, api_key, progress)

        # ── Step 4: Complete ──
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
            "Worker %s completed: fetched=%d, enriched=%d, pushed=%d, failed=%d",
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
        logger.info("Worker %s cancelled", execution_id)

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
    await exec_repo.create(
        {
            "id": execution_id,
            "integration_system_id": system.id,
            "status": "pending",
            "date_from": date_from,
            "date_to": date_to,
            "triggered_by": triggered_by,
        }
    )
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


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Jobs — 3-stage async background pipeline (fetch → enrich → push)
# ═══════════════════════════════════════════════════════════════════════════════

# Circuit breaker state for Job 2 (enrich)
_enrich_circuit_paused: bool = False
_enrich_consecutive_failures: int = 0


def is_enrich_paused() -> bool:
    return _enrich_circuit_paused


def get_enrich_consecutive_failures() -> int:
    return _enrich_consecutive_failures


def reset_enrich_circuit() -> None:
    """Reset circuit breaker — called after manual intervention or API reset."""
    global _enrich_circuit_paused, _enrich_consecutive_failures
    _enrich_circuit_paused = False
    _enrich_consecutive_failures = 0
    logger.info("Enrich circuit breaker reset")


async def job_fetch_csv_import() -> None:
    """Job 1: Fetch teleconsulta appointments via CSV export and create records.

    Uses EXECUTANTE/SOLICITANTE profile. Creates records with status 'awaiting_enrichment'.
    Deduplicates by regulation_code (skips if record already exists with any status).
    """
    from regulahub.config import get_pipeline_settings
    from regulahub.db.engine import get_session_factory
    from regulahub.db.repositories.integration_appointment import IntegrationAppointmentRepository

    settings = get_pipeline_settings()
    session_factory = get_session_factory()

    async with session_factory() as db_session:
        credentials = await _resolve_credentials(db_session, "EXECUTANTE/SOLICITANTE")
        sys_repo = RegulationSystemRepository(db_session)
        system = await sys_repo.get_by_code(settings.pipeline_system_code)
        if not system:
            logger.error("Job 1 (Fetch): system '%s' not found", settings.pipeline_system_code)
            return
        system_id = system.id

    today = date.today()
    date_from = today + timedelta(days=1)
    date_to = today + timedelta(days=settings.pipeline_fetch_days_ahead)

    progress = ExecutionProgress(execution_id=uuid.uuid4())
    rows = await _fetch_appointments(credentials, date_from, date_to, progress)

    if not rows:
        logger.info("Job 1 (Fetch): no teleconsulta appointments for %s to %s", date_from, date_to)
        return

    created_count = 0
    skipped_count = 0
    async with session_factory() as db_session:
        repo = IntegrationAppointmentRepository(db_session)

        for row in rows:
            if not row.solicitacao:
                continue

            if await repo.exists_by_regulation_code(row.solicitacao):
                skipped_count += 1
                continue

            appt_date = date_from
            appt_time = None
            try:
                parsed_date = datetime.strptime(row.data_agendamento.replace(".", "/"), "%d/%m/%Y")
                appt_date = parsed_date.date()
                if row.hr_agendamento:
                    parsed_time = datetime.strptime(row.hr_agendamento, "%H:%M")
                    appt_time = parsed_time.time()
            except (ValueError, AttributeError):
                pass

            patient_name = row.nome.strip() if row.nome else "DESCONHECIDO"

            await repo.create(
                {
                    "integration_system_id": system_id,
                    "regulation_code": row.solicitacao,
                    "patient_name": patient_name,
                    "patient_cns": row.cns or "",
                    "patient_birth_date": (row.dt_nascimento or "").replace(".", "/").strip(),
                    "patient_phone": row.telefone or "",
                    "patient_mother_name": row.nome_mae or "",
                    "appointment_date": appt_date,
                    "appointment_time": appt_time,
                    "procedure_name": row.descricao_procedimento,
                    "department_solicitor": row.unidade_fantasia or "",
                    "department_solicitor_cnes": row.cnes_solicitante or "",
                    "doctor_name": row.nome_profissional_executante or "",
                    "status": "awaiting_enrichment",
                    "source_data": {
                        "sisreg_csv": {
                            "solicitacao": row.solicitacao,
                            "descricao_procedimento": row.descricao_procedimento,
                        },
                    },
                    "integration_data": {},
                    "reference_date": appt_date,
                }
            )
            created_count += 1

        await db_session.commit()

    logger.info(
        "Job 1 (Fetch): created %d, skipped %d existing (from %d CSV rows, %s to %s)",
        created_count,
        skipped_count,
        len(rows),
        date_from,
        date_to,
    )


async def job_enrich_detail() -> None:
    """Job 2: Enrich appointments with SisReg detail + CADSUS data.

    Uses VIDEOFONISTA profile. Queries 'awaiting_enrichment' records.
    Circuit breaker: N consecutive detail() failures → pause + Slack alert.
    """
    global _enrich_circuit_paused, _enrich_consecutive_failures

    if _enrich_circuit_paused:
        logger.info("Job 2 (Enrich): circuit breaker PAUSED, skipping cycle")
        return

    import re as _re

    from regulahub.config import get_cadsus_settings, get_pipeline_settings
    from regulahub.db.engine import get_session_factory
    from regulahub.db.models import IntegrationExecutionMapping
    from regulahub.db.repositories.integration_appointment import IntegrationAppointmentRepository
    from regulahub.db.repositories.integration_mapping import IntegrationMappingRepository
    from regulahub.services.slack_notifier import send_slack_alert
    from regulahub.sisreg.client import SisregClient, SisregLoginError

    settings = get_pipeline_settings()
    session_factory = get_session_factory()
    max_failures = settings.pipeline_enrich_max_consecutive_failures

    # Load credentials and mappings
    async with session_factory() as db_session:
        try:
            videofonista_creds = await _resolve_credentials(db_session, "VIDEOFONISTA")
        except RuntimeError:
            logger.warning("Job 2 (Enrich): no VIDEOFONISTA credentials configured")
            return

        mapping_repo = IntegrationMappingRepository(db_session)
        dept_list = await mapping_repo.list_all_departments()
        proc_list = await mapping_repo.list_all_procedures()
        departments = {d.department_name.upper().strip(): d for d in dept_list}
        departments_by_cnes = {d.cnes_code.strip(): d for d in dept_list if d.cnes_code}
        procedures = {p.procedure_name.upper().strip(): p for p in proc_list}

        from sqlalchemy import select

        stmt = select(IntegrationExecutionMapping).where(IntegrationExecutionMapping.is_active.is_(True))
        result = await db_session.execute(stmt)
        execution_mappings = {m.requester_cnes: m for m in result.scalars().all()}

    # Get batch of awaiting_enrichment
    async with session_factory() as db_session:
        repo = IntegrationAppointmentRepository(db_session)
        appointments = await repo.list_by_status("awaiting_enrichment", limit=settings.pipeline_enrich_batch_size)

    if not appointments:
        logger.info("Job 2 (Enrich): no appointments awaiting enrichment")
        return

    logger.info("Job 2 (Enrich): processing %d appointments", len(appointments))
    enriched_count = 0
    failed_count = 0

    username, password = videofonista_creds[0]
    try:
        async with SisregClient(SISREG_BASE_URL, username, password, "VIDEOFONISTA") as sisreg:
            # CADSUS client
            cadsus_settings = get_cadsus_settings()
            cadsus_client = None
            if cadsus_settings.cadsus_enabled:
                from regulahub.integrations.cadsus_client import CadsusClient

                cadsus_client = CadsusClient(settings=cadsus_settings)

            from zoneinfo import ZoneInfo

            manaus_tz = ZoneInfo("America/Manaus")

            for appt in appointments:
                # ── Detail fetch with circuit breaker ──
                detail = None
                try:
                    detail = await sisreg.detail(appt.regulation_code)
                    _enrich_consecutive_failures = 0
                except Exception:
                    _enrich_consecutive_failures += 1
                    logger.warning(
                        "Job 2: detail() failed for %s (%d consecutive failures)",
                        appt.regulation_code,
                        _enrich_consecutive_failures,
                    )
                    if _enrich_consecutive_failures >= max_failures:
                        _enrich_circuit_paused = True
                        await send_slack_alert(
                            "Enrichment circuit breaker TRIPPED — probable reCAPTCHA block",
                            context={
                                "Consecutive failures": str(_enrich_consecutive_failures),
                                "Last code": appt.regulation_code,
                                "Action": "Resolve reCAPTCHA manually, then reset via API",
                            },
                        )
                        logger.error("Job 2: circuit breaker tripped after %d failures", _enrich_consecutive_failures)
                        return
                    continue  # Keep awaiting_enrichment, retry next cycle

                # ── CADSUS lookup ──
                cadsus = {}
                if cadsus_client and appt.patient_cns:
                    try:
                        patient = await cadsus_client.get_patient_by_cns(appt.patient_cns)
                        if patient and patient.cpf:
                            cadsus = {
                                "cpf": patient.cpf or "",
                                "phone": patient.phone or "",
                                "mother_name": patient.mother_name or "",
                                "birth_date": patient.birth_date or "",
                            }
                    except Exception:
                        logger.warning("Job 2: CADSUS failed for %s", appt.regulation_code)

                # ── Resolve executor ──
                executor_name = (detail.exec_unit_name or "").upper().strip() if detail else ""
                executor_cnes = (detail.exec_unit_cnes or "").strip() if detail else ""
                confirmation_key = detail.confirmation_key if detail else ""
                soliciting_cnes = (detail.req_unit_cnes or appt.department_solicitor_cnes or "").strip()

                if not executor_name and not executor_cnes:
                    async with session_factory() as db_session:
                        repo = IntegrationAppointmentRepository(db_session)
                        await repo.update_status(
                            appt.id,
                            status="mapping_error",
                            error_message=f"SisReg detail missing executor unit for code {appt.regulation_code}",
                            error_category="missing_detail_executor",
                        )
                        await db_session.commit()
                    failed_count += 1
                    continue

                executor_dept = departments.get(executor_name) if executor_name else None
                if not executor_dept and executor_cnes:
                    executor_dept = departments_by_cnes.get(executor_cnes)

                # Resolve group_id and location
                group_id = ""
                location = ""
                is_remote = True

                if executor_dept:
                    if executor_dept.department_type == "PARTIALINTEGRATION" and soliciting_cnes:
                        mapping = execution_mappings.get(soliciting_cnes)
                        if mapping:
                            group_id = str(mapping.group_id)
                            loc_addr = mapping.executor_address or ""
                            location = f"{mapping.executor_name} - {loc_addr}" if loc_addr else mapping.executor_name
                        else:
                            async with session_factory() as db_session:
                                repo = IntegrationAppointmentRepository(db_session)
                                await repo.update_status(
                                    appt.id,
                                    status="mapping_error",
                                    error_message=(
                                        f"Interior: no execution mapping for CNES "
                                        f"{soliciting_cnes} ({appt.department_solicitor})"
                                    ),
                                    error_category="missing_execution_mapping",
                                )
                                await db_session.commit()
                            failed_count += 1
                            continue
                    else:
                        group_id = str(executor_dept.group_id)
                        is_remote = executor_dept.is_remote
                        addr = getattr(executor_dept, "department_address", "") or ""
                        location = (
                            f"{executor_dept.department_name} - {addr}" if addr else executor_dept.department_name
                        )
                else:
                    async with session_factory() as db_session:
                        repo = IntegrationAppointmentRepository(db_session)
                        await repo.update_status(
                            appt.id,
                            status="mapping_error",
                            error_message=f"Executor not in departments table (name='{executor_name}', cnes='{executor_cnes}')",  # noqa: E501
                            error_category="unmapped_executor_department",
                        )
                        await db_session.commit()
                    failed_count += 1
                    continue

                if not group_id:
                    async with session_factory() as db_session:
                        repo = IntegrationAppointmentRepository(db_session)
                        await repo.update_status(
                            appt.id,
                            status="mapping_error",
                            error_message=f"Resolved department but group_id empty for {appt.regulation_code}",
                            error_category="missing_group_id",
                        )
                        await db_session.commit()
                    failed_count += 1
                    continue

                # Resolve procedure
                proc = procedures.get((appt.procedure_name or "").upper().strip())
                if not proc:
                    async with session_factory() as db_session:
                        repo = IntegrationAppointmentRepository(db_session)
                        await repo.update_status(
                            appt.id,
                            status="data_error",
                            error_message=f"Procedure not mapped: {appt.procedure_name}",
                            error_category="unmapped_procedure",
                        )
                        await db_session.commit()
                    failed_count += 1
                    continue

                preference = "ONLINE" if is_remote else "PRESENCIAL"

                # Phone: prefer CADSUS, fallback to existing
                raw_phone = cadsus.get("phone", "") or appt.patient_phone or ""
                phone_digits = _re.sub(r"\D", "", raw_phone)
                phone = phone_digits if 10 <= len(phone_digits) <= 15 else "00000000000"

                # Birth date: prefer CADSUS, fallback to existing
                birth_date = cadsus.get("birth_date", "") or appt.patient_birth_date or ""
                birth_date = birth_date.replace(".", "/").strip() if birth_date else ""

                # Build external_id
                external_id = f"{appt.regulation_code}-{confirmation_key}" if confirmation_key else appt.regulation_code

                # Parse appointment datetime for ISO format
                start_date_str = ""
                end_date_str = ""
                if appt.appointment_date:
                    hour = appt.appointment_time.hour if appt.appointment_time else 0
                    minute = appt.appointment_time.minute if appt.appointment_time else 0
                    start_dt = datetime(
                        appt.appointment_date.year,
                        appt.appointment_date.month,
                        appt.appointment_date.day,
                        hour,
                        minute,
                        tzinfo=manaus_tz,
                    )
                    end_dt = start_dt + timedelta(minutes=30)
                    start_date_str = start_dt.isoformat()
                    end_date_str = end_dt.isoformat()

                # ── Update record with enriched data ──
                async with session_factory() as db_session:
                    repo = IntegrationAppointmentRepository(db_session)
                    record = await repo.get_by_id(appt.id)
                    if not record:
                        continue

                    record.confirmation_key = confirmation_key
                    record.external_id = external_id
                    record.patient_cpf = cadsus.get("cpf", record.patient_cpf or "")
                    record.patient_phone = phone
                    record.patient_birth_date = birth_date
                    record.patient_mother_name = cadsus.get("mother_name", record.patient_mother_name or "")
                    record.department_executor = executor_dept.department_name if executor_dept else executor_name
                    record.department_executor_cnes = executor_dept.cnes_code if executor_dept else executor_cnes
                    record.doctor_name = detail.sol_doctor_name or record.doctor_name or ""
                    record.integration_data = {
                        **(record.integration_data or {}),
                        "group_id": group_id,
                        "work_scale_name": proc.work_scale_name,
                        "preference_of_service": preference,
                        "location_of_service": location,
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                    }
                    record.status = "awaiting_integration"
                    record.error_message = None
                    record.error_category = None
                    record.updated_at = datetime.now(UTC)
                    await db_session.flush()
                    await db_session.commit()

                enriched_count += 1

    except SisregLoginError:
        logger.error("Job 2: VIDEOFONISTA login failed — session likely blocked")
        _enrich_circuit_paused = True
        _enrich_consecutive_failures = max_failures
        from regulahub.services.slack_notifier import send_slack_alert

        await send_slack_alert(
            "VIDEOFONISTA login failed — session blocked (reCAPTCHA?)",
            context={"Action": "Resolve manually and reset circuit breaker via API"},
        )
    except Exception:
        logger.exception("Job 2 (Enrich): unexpected error")

    logger.info("Job 2 (Enrich): enriched=%d, failed=%d", enriched_count, failed_count)


def _build_push_payload_from_record(appt: object) -> dict | None:
    """Convert a DB IntegrationAppointment into the dict format for IntegrationPushClient."""
    int_data = appt.integration_data or {}
    group_id = int_data.get("group_id", "")
    if not group_id:
        return None

    name_parts = (appt.patient_name or "").strip().split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    return {
        "code": appt.regulation_code,
        "external_id": appt.external_id or appt.regulation_code,
        "confirmation_key": appt.confirmation_key or "",
        "patient_cns": appt.patient_cns or "",
        "patient_cpf": appt.patient_cpf or "",
        "patient_first_name": first_name,
        "patient_last_name": last_name,
        "patient_birth_date": appt.patient_birth_date or "",
        "patient_mother_name": appt.patient_mother_name or "",
        "patient_phone": appt.patient_phone or "",
        "doctor_name": appt.doctor_name or "",
        "group_id": group_id,
        "work_scale_name": int_data.get("work_scale_name", ""),
        "preference_of_service": int_data.get("preference_of_service", "ONLINE"),
        "location_of_service": int_data.get("location_of_service", ""),
        "start_date": int_data.get("start_date", ""),
        "end_date": int_data.get("end_date", ""),
    }


async def expire_pending_reviews() -> int:
    """Transition pending_review appointments past their date to expired. Returns count."""
    from regulahub.db.engine import get_session_factory
    from regulahub.db.repositories.integration_appointment import IntegrationAppointmentRepository

    session_factory = get_session_factory()
    async with session_factory() as db_session:
        repo = IntegrationAppointmentRepository(db_session)
        pending = await repo.list_by_status("pending_review", limit=500)
        today = date.today()
        expired_count = 0
        for appt in pending:
            if appt.appointment_date and appt.appointment_date < today:
                await repo.update_status(
                    appt.id,
                    status="expired",
                    error_message="Agendamento expirado: campo obrigatorio nao resolvido antes da data",
                    error_category="expired_review",
                )
                expired_count += 1
        if expired_count:
            await db_session.commit()
            logger.info("Expired %d pending_review appointments past their date", expired_count)
    return expired_count


async def job_push_integration() -> None:
    """Job 3: Push enriched appointments to integration system.

    Queries 'awaiting_integration' (and legacy 'pending') records, pushes via IntegrationPushClient.
    Expires pending_review appointments past their date before processing.
    """
    # Expire stale pending_review records before pushing
    await expire_pending_reviews()

    from regulahub.config import get_integration_settings, get_pipeline_settings
    from regulahub.db.engine import get_session_factory
    from regulahub.db.repositories.integration_appointment import IntegrationAppointmentRepository

    settings = get_pipeline_settings()
    integration_settings = get_integration_settings()
    api_key = integration_settings.integration_api_key
    if not api_key:
        logger.error("Job 3 (Push): INTEGRATION_API_KEY not configured")
        return

    session_factory = get_session_factory()

    # Get batch of awaiting_integration + legacy pending
    async with session_factory() as db_session:
        repo = IntegrationAppointmentRepository(db_session)
        appointments = await repo.list_by_status("awaiting_integration", limit=settings.pipeline_push_batch_size)
        pending = await repo.list_by_status(
            "pending", limit=max(0, settings.pipeline_push_batch_size - len(appointments))
        )
        appointments.extend(pending)

    if not appointments:
        logger.info("Job 3 (Push): no appointments awaiting integration")
        return

    logger.info("Job 3 (Push): processing %d appointments", len(appointments))
    pushed_count = 0
    failed_count = 0

    async with IntegrationPushClient(
        core_api_base_url=integration_settings.integration_core_api_url,
        auth_api_base_url=integration_settings.integration_auth_api_url,
        api_key=api_key,
    ) as client:
        for appt in appointments:
            push_data = _build_push_payload_from_record(appt)
            if not push_data:
                async with session_factory() as db_session:
                    repo = IntegrationAppointmentRepository(db_session)
                    await repo.update_status(
                        appt.id,
                        status="data_error",
                        error_message="Missing group_id or required push data",
                        error_category="data",
                    )
                    await db_session.commit()
                failed_count += 1
                continue

            result = await client.process_appointment(push_data)

            async with session_factory() as db_session:
                repo = IntegrationAppointmentRepository(db_session)
                existing = await repo.get_by_id(appt.id)
                if not existing:
                    continue

                if result.success:
                    pushed_count += 1
                    status = "skipped" if result.appointment_skipped else "integrated"
                    merged_data = dict(existing.integration_data or {})
                    merged_data.update(
                        {
                            "patient_id": result.patient_id,
                            "appointment_id": result.appointment_id,
                            "is_new_account": result.is_new_account,
                        }
                    )
                    await repo.update_status(appt.id, status, integration_data=merged_data)
                else:
                    failed_count += 1
                    status = f"{result.error_category}_error" if result.error_category else "appointment_error"
                    await repo.update_status(
                        appt.id,
                        status,
                        error_message=result.error,
                        error_category=result.error_category or None,
                    )

                await db_session.commit()

    logger.info("Job 3 (Push): pushed=%d, failed=%d", pushed_count, failed_count)


# ── Background job scheduler ──────────────────────────────────────────────────

_pipeline_tasks: list[asyncio.Task] = []


async def _run_job_loop(job_name: str, job_fn, interval_seconds: int, enabled_fn) -> None:
    """Generic polling loop for a pipeline job."""
    logger.info("Pipeline job '%s' starting (interval=%ds)", job_name, interval_seconds)
    # Initial delay to let the app fully start before first run
    await asyncio.sleep(30)
    while True:
        try:
            if enabled_fn():
                logger.info("Pipeline job '%s' running", job_name)
                await job_fn()
            else:
                logger.debug("Pipeline job '%s' disabled, skipping", job_name)
        except Exception:
            logger.exception("Pipeline job '%s' unhandled error", job_name)
        await asyncio.sleep(interval_seconds)


_job_locks: dict[str, asyncio.Lock] = {}


async def _guarded_job(name: str, fn) -> None:
    """Run job with lock to prevent concurrent execution of the same job."""
    if name not in _job_locks:
        _job_locks[name] = asyncio.Lock()
    lock = _job_locks[name]
    if lock.locked():
        logger.info("Pipeline job '%s' still running, skipping this cycle", name)
        return
    async with lock:
        await fn()


async def start_pipeline_jobs() -> None:
    """Start all 3 pipeline jobs as background tasks. Called from FastAPI lifespan."""
    from regulahub.config import get_pipeline_settings

    settings = get_pipeline_settings()

    async def fetch_guarded():
        await _guarded_job("fetch", job_fetch_csv_import)

    async def enrich_guarded():
        await _guarded_job("enrich", job_enrich_detail)

    async def push_guarded():
        await _guarded_job("push", job_push_integration)

    _pipeline_tasks.append(
        asyncio.create_task(
            _run_job_loop(
                "fetch",
                fetch_guarded,
                settings.pipeline_fetch_interval_seconds,
                lambda: settings.pipeline_fetch_enabled,
            ),
            name="pipeline-fetch",
        )
    )
    _pipeline_tasks.append(
        asyncio.create_task(
            _run_job_loop(
                "enrich",
                enrich_guarded,
                settings.pipeline_enrich_interval_seconds,
                lambda: settings.pipeline_enrich_enabled,
            ),
            name="pipeline-enrich",
        )
    )
    _pipeline_tasks.append(
        asyncio.create_task(
            _run_job_loop(
                "push", push_guarded, settings.pipeline_push_interval_seconds, lambda: settings.pipeline_push_enabled
            ),
            name="pipeline-push",
        )
    )
    logger.info(
        "Pipeline jobs started: fetch=%ds, enrich=%ds, push=%ds",
        settings.pipeline_fetch_interval_seconds,
        settings.pipeline_enrich_interval_seconds,
        settings.pipeline_push_interval_seconds,
    )
