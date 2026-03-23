"""Integration worker service — fetches SisReg appointments and pushes to integration systems.

Pipeline: resolve credentials → parallel SisReg search → enrich (detail + CadWeb) → push to integration.
Runs as an in-process async task triggered by the API. Status tracked in-memory + persisted to DB.
"""

import asyncio
import dataclasses
import logging
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.models import System, SystemEndpoint
from regulahub.db.repositories.credential import CredentialRepository
from regulahub.db.repositories.integration_execution import IntegrationExecutionRepository
from regulahub.db.repositories.regulation_system import RegulationSystemRepository
from regulahub.services.integration_push_client import BatchPushResult, IntegrationPushClient
from regulahub.sisreg.client import SisregClient, SisregLoginError
from regulahub.sisreg.models import AppointmentDetail, AppointmentListing, CadwebPatientData, SearchFilters
from regulahub.utils.encryption import decrypt_password
from regulahub.utils.masking import mask_username

logger = logging.getLogger(__name__)

SISREG_BASE_URL = "https://sisregiii.saude.gov.br"


@dataclasses.dataclass
class ExecutionProgress:
    """In-memory execution progress for real-time polling."""

    execution_id: uuid.UUID
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


async def _resolve_credentials(db_session: AsyncSession) -> list[tuple[str, str]]:
    """Resolve all active VIDEOFONISTA credentials for SISREG."""
    repo = CredentialRepository(db_session)
    creds = await repo.get_active_by_system_and_profile("SISREG", "VIDEOFONISTA")

    if not creds:
        raise RuntimeError("No VIDEOFONISTA credentials configured for SISREG")

    resolved: list[tuple[str, str]] = []
    for cred in creds:
        try:
            pw = decrypt_password(cred.encrypted_password)
            resolved.append((cred.username, pw))
        except ValueError:
            logger.warning("Failed to decrypt credential for operator %s", mask_username(cred.username))

    if not resolved:
        raise RuntimeError("All VIDEOFONISTA credentials failed decryption")

    return resolved


async def _search_single_day(
    username: str,
    password: str,
    date_br: str,
) -> list[AppointmentListing]:
    """Search SisReg for a single day with a single operator credential."""
    user_hash = mask_username(username)
    filters = SearchFilters(
        date_from=date_br,
        date_to=date_br,
        procedure_description="teleconsulta",
        situation="7",
        profile_type="VIDEOFONISTA",
        usernames=[username],
    )
    try:
        async with SisregClient(SISREG_BASE_URL, username, password, "VIDEOFONISTA") as client:
            result = await client.search(filters)
            logger.info("Worker search: operator %s, date %s, %d items", user_hash, date_br, len(result.items))
            return result.items
    except SisregLoginError:
        logger.warning("Worker SisReg login failed for operator %s on %s", user_hash, date_br)
        return []
    except Exception:
        logger.exception("Worker SisReg search error for operator %s on %s", user_hash, date_br)
        return []


async def _fetch_appointments(
    credentials: list[tuple[str, str]],
    date_from: date,
    date_to: date,
    progress: ExecutionProgress,
) -> list[AppointmentListing]:
    """Fetch appointments from SisReg for a date range.

    Searches sequentially per day using a single SisReg session to avoid
    concurrent login conflicts (SisReg invalidates previous sessions).
    """
    progress.stage = "fetching"

    # Generate all dates in range
    dates: list[date] = []
    current = date_from
    while current <= date_to:
        dates.append(current)
        current += timedelta(days=1)

    # Search each day sequentially with the first credential
    username, password = credentials[0]
    results: list[list[AppointmentListing]] = []
    for d in dates:
        items = await _search_single_day(username, password, d.strftime("%d/%m/%Y"))
        results.append(items)

    # Merge and deduplicate by code
    seen_codes: set[str] = set()
    merged: list[AppointmentListing] = []
    for items in results:
        for item in items:
            if item.code not in seen_codes:
                seen_codes.add(item.code)
                merged.append(item)

    progress.total_fetched = len(merged)
    logger.info("Worker fetch: %d unique teleconsulta appointments for %s to %s", len(merged), date_from, date_to)
    return merged


async def _fetch_details_for_batch(
    codes: list[str],
    username: str,
    password: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, tuple[AppointmentDetail, CadwebPatientData | None]]:
    """Fetch detail + CadWeb for a batch of codes using a single SisReg session."""
    result: dict[str, tuple[AppointmentDetail, CadwebPatientData | None]] = {}
    user_hash = mask_username(username)
    cadweb_cache: dict[str, CadwebPatientData | None] = {}

    async with semaphore:
        try:
            async with SisregClient(SISREG_BASE_URL, username, password, "VIDEOFONISTA") as client:
                for code in codes:
                    try:
                        detail = await client.detail(code)
                        cadweb = None
                        cns = detail.patient_cns
                        if cns:
                            if cns in cadweb_cache:
                                cadweb = cadweb_cache[cns]
                            else:
                                try:
                                    cadweb = await client.cadweb_lookup(cns)
                                except Exception:
                                    logger.warning("Worker CadWeb failed for code %s (operator %s)", code, user_hash)
                                cadweb_cache[cns] = cadweb
                        result[code] = (detail, cadweb)
                    except Exception:
                        logger.warning("Worker enrichment failed for code %s (operator %s)", code, user_hash)
        except SisregLoginError:
            logger.warning("Worker enrichment login failed for operator %s, skipping %d codes", user_hash, len(codes))
        except Exception:
            logger.exception("Worker enrichment session error for operator %s", user_hash)

    return result


async def _enrich_appointments(
    listings: list[AppointmentListing],
    credentials: list[tuple[str, str]],
    progress: ExecutionProgress,
) -> list[EnrichedAppointment]:
    """Enrich listings with detail + CadWeb data via parallel SisReg sessions."""
    if not listings:
        return []

    progress.stage = "enriching"
    codes = [item.code for item in listings]
    semaphore = asyncio.Semaphore(5)

    # Round-robin distribute codes across credentials
    batches: dict[int, list[str]] = {i: [] for i in range(len(credentials))}
    for idx, code in enumerate(codes):
        batches[idx % len(credentials)].append(code)

    tasks = [
        _fetch_details_for_batch(batch_codes, credentials[cred_idx][0], credentials[cred_idx][1], semaphore)
        for cred_idx, batch_codes in batches.items()
        if batch_codes
    ]

    results = await asyncio.gather(*tasks)
    enrichment: dict[str, tuple[AppointmentDetail, CadwebPatientData | None]] = {}
    for result_dict in results:
        enrichment.update(result_dict)

    # Build enriched appointments
    enriched: list[EnrichedAppointment] = []
    listing_map = {item.code: item for item in listings}

    for code, listing in listing_map.items():
        detail, cadweb = enrichment.get(code, (None, None))

        phone = ""
        phone_ddd = ""
        if cadweb and cadweb.phone_ddd and cadweb.phone_number:
            phone = cadweb.phone_number
            phone_ddd = cadweb.phone_ddd
        elif detail and detail.best_phone:
            phone = detail.best_phone.number
            phone_ddd = detail.best_phone.ddd

        enriched.append(
            EnrichedAppointment(
                code=listing.code,
                patient_cns=detail.patient_cns if detail else "",
                patient_name=detail.patient_name or listing.patient_name if detail else listing.patient_name,
                patient_cpf=cadweb.cpf if cadweb else "",
                patient_birth_date=detail.patient_birth_date if detail else "",
                patient_mother_name=cadweb.mother_name if cadweb else "",
                patient_phone=phone,
                patient_phone_ddd=phone_ddd,
                doctor_name=detail.doctor_name if detail else "",
                appointment_date=detail.appointment_date if detail else listing.execution_date,
                procedure=detail.procedure_name or listing.procedure if detail else listing.procedure,
                department=detail.department or listing.dept_execute if detail else listing.dept_execute,
                department_solicitation=detail.req_unit_name or listing.dept_solicitation
                if detail
                else listing.dept_solicitation,
                confirmation_key=detail.confirmation_key if detail else "",
                status=detail.sol_status or listing.status if detail else listing.status,
            )
        )

    progress.total_enriched = sum(1 for e in enriched if e.patient_cns)
    logger.info("Worker enrichment: %d/%d appointments enriched", progress.total_enriched, len(enriched))
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

    Pipeline: resolve credentials → fetch appointments → enrich → push to integration.
    """
    from regulahub.db.engine import get_session_factory

    progress = ExecutionProgress(execution_id=execution_id, started_at=datetime.now(UTC))
    _active_executions[execution_id] = progress

    session_factory = get_session_factory()

    try:
        async with session_factory() as db_session:
            # Update status to running
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

        # Step 2: Fetch appointments (no DB needed — pure SisReg HTTP)
        listings = await _fetch_appointments(credentials, date_from, date_to, progress)

        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_progress(execution_id, progress.to_dict())
            await db_session.commit()

        if progress.cancelled:
            raise asyncio.CancelledError

        # Step 3: Enrich appointments (no DB needed — pure SisReg HTTP)
        enriched = await _enrich_appointments(listings, credentials, progress)

        async with session_factory() as db_session:
            repo = IntegrationExecutionRepository(db_session)
            await repo.update_progress(execution_id, progress.to_dict())
            await db_session.commit()

        if progress.cancelled:
            raise asyncio.CancelledError

        # Step 4: Push to integration system (pure HTTP)
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
    """Trigger a new worker execution. Returns execution ID.

    Creates the DB record and starts the background task.
    """
    # Resolve system to get its ID
    system_repo = RegulationSystemRepository(db_session)
    system = await system_repo.get_by_code(system_code)
    if not system:
        raise ValueError(f"Integration system '{system_code}' not found")

    # Check for running executions
    exec_repo = IntegrationExecutionRepository(db_session)
    if await exec_repo.has_running_execution(system.id):
        raise RuntimeError(f"An execution is already running for system '{system_code}'")

    # Create execution record
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

    # Start background task (worker creates its own DB session)
    task = asyncio.create_task(
        execute_integration(execution_id, system_code, date_from, date_to),
        name=f"integration-worker-{execution_id}",
    )
    _background_tasks[execution_id] = task

    # Clean up reference when done
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
