"""Schedule export service — multi-operator CSV export from SisReg."""

import asyncio
import csv
import io
import logging
from datetime import date as date_type

from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.repositories.cached_export import CachedExportRepository
from regulahub.db.repositories.credential import CredentialRepository
from regulahub.services.credential_service import CredentialNotFoundError
from regulahub.sisreg.client import SisregClient, SisregLoginError
from regulahub.sisreg.export_parser import EXPORT_COLUMNS, parse_export_csv
from regulahub.sisreg.models import EnrichedExportRow, ExportFilters, ScheduleExportResponse, ScheduleExportRow
from regulahub.utils.encryption import decrypt_password
from regulahub.utils.masking import mask_username

logger = logging.getLogger(__name__)

SISREG_BASE_URL = "https://sisregiii.saude.gov.br"


async def _resolve_solicitante_credentials(
    usernames: list[str],
    profile_type: str,
    db_session: AsyncSession,
) -> list[tuple[str, str]]:
    """Resolve credentials by username for the given profile type."""
    repo = CredentialRepository(db_session)
    creds = await repo.get_active_by_system_and_profile("SISREG", profile_type)

    if not creds:
        raise CredentialNotFoundError(f"No {profile_type} credentials configured for SISREG")

    username_set = set(usernames)
    resolved: list[tuple[str, str]] = []
    for cred in creds:
        if cred.username not in username_set:
            continue
        try:
            pw = decrypt_password(cred.encrypted_password)
            resolved.append((cred.username, pw))
        except ValueError:
            logger.warning("Failed to decrypt credential for operator %s, skipping", mask_username(cred.username))

    if not resolved:
        raise CredentialNotFoundError(f"No valid {profile_type} credentials found for requested usernames")

    return resolved


async def _export_single_operator(
    username: str,
    password: str,
    profile_type: str,
    date_from: str,
    date_to: str,
    *,
    cpf: str = "0",
    procedimento: str = "",
    file_type: int = 1,
) -> list[ScheduleExportRow]:
    """Export schedule data for a single operator."""
    user_hash = mask_username(username)
    try:
        async with SisregClient(SISREG_BASE_URL, username, password, profile_type) as client:
            raw_bytes = await client.export_schedule(
                date_from,
                date_to,
                cpf=cpf,
                procedimento=procedimento,
                file_type=file_type,
            )
            rows = parse_export_csv(raw_bytes)
            logger.info("Export operator %s returned %d rows", user_hash, len(rows))
            return rows
    except SisregLoginError:
        logger.warning("Export login failed for operator %s, skipping", user_hash)
        return []
    except Exception:
        logger.exception("Export error for operator %s, skipping", user_hash)
        return []


async def export_single_operator_resolved(
    username: str,
    password: str,
    profile_type: str,
    date_from: str,
    date_to: str,
) -> list[ScheduleExportRow]:
    """Export schedule data for a single operator (with credential already resolved).

    Unlike _export_single_operator, this raises exceptions instead of swallowing them,
    so the route can return proper HTTP error codes.
    """
    async with SisregClient(SISREG_BASE_URL, username, password, profile_type) as client:
        raw_bytes = await client.export_schedule(date_from, date_to)
        return parse_export_csv(raw_bytes)


async def export_schedules(
    filters: ExportFilters,
    db_session: AsyncSession,
) -> ScheduleExportResponse:
    """Export schedules from SisReg using multiple operator credentials in parallel.

    - Resolves credentials for all requested usernames
    - Exports in parallel with semaphore(5)
    - Merges and deduplicates by solicitacao (first-seen wins)
    """
    credentials = await _resolve_solicitante_credentials(filters.usernames, filters.profile_type, db_session)

    semaphore = asyncio.Semaphore(5)
    operators_succeeded = 0

    async def _guarded_export(username: str, password: str) -> list[ScheduleExportRow]:
        async with semaphore:
            return await _export_single_operator(
                username,
                password,
                filters.profile_type,
                filters.date_from,
                filters.date_to,
                cpf=filters.cpf,
                procedimento=filters.procedimento,
                file_type=filters.file_type,
            )

    tasks = [_guarded_export(u, p) for u, p in credentials]
    results = await asyncio.gather(*tasks)

    # Merge and deduplicate by solicitacao
    seen: set[str] = set()
    merged: list[ScheduleExportRow] = []
    for operator_rows in results:
        if operator_rows:
            operators_succeeded += 1
        for row in operator_rows:
            if row.solicitacao and row.solicitacao not in seen:
                seen.add(row.solicitacao)
                merged.append(row)

    logger.info(
        "Schedule export: %d operators queried, %d succeeded, %d unique rows",
        len(credentials),
        operators_succeeded,
        len(merged),
    )

    return ScheduleExportResponse(
        items=merged,
        total=len(merged),
        operators_queried=len(credentials),
        operators_succeeded=operators_succeeded,
    )


def build_csv_bytes(rows: list[ScheduleExportRow]) -> bytes:
    """Rebuild CSV from ScheduleExportRow list with semicolon separator."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")

    # Header
    writer.writerow(EXPORT_COLUMNS)

    # Data rows
    for row in rows:
        writer.writerow([getattr(row, col) for col in EXPORT_COLUMNS])

    return output.getvalue().encode("utf-8")


def build_txt_bytes(rows: list[ScheduleExportRow]) -> bytes:
    """Rebuild TXT from ScheduleExportRow list with tab separator."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", lineterminator="\r\n")

    # Header
    writer.writerow(EXPORT_COLUMNS)

    # Data rows
    for row in rows:
        writer.writerow([getattr(row, col) for col in EXPORT_COLUMNS])

    return output.getvalue().encode("utf-8")


def _parse_date_ddmmyyyy(value: str) -> date_type | None:
    """Parse dd/MM/yyyy or dd.MM.yyyy string to date object. Returns None on failure."""
    try:
        import re

        parts = re.split(r"[/.]", value.strip())
        if len(parts) != 3:
            return None
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        return date_type(year, month, day)
    except (ValueError, IndexError):
        return None


async def get_cached_exports(
    date_from: str,
    date_to: str,
    procedure_filter: str | None,
    db_session: AsyncSession,
) -> list[ScheduleExportRow | EnrichedExportRow]:
    """Fetch cached rows from DB, convert row_data JSONB back to export rows.

    If the cached row_data contains enrichment fields (cpf_paciente, etc.),
    deserializes as EnrichedExportRow so the frontend can display them.
    """
    from_date = _parse_date_ddmmyyyy(date_from)
    to_date = _parse_date_ddmmyyyy(date_to)
    if not from_date or not to_date:
        logger.warning("Invalid date range for cache query: %s — %s", date_from, date_to)
        return []

    repo = CachedExportRepository(db_session)
    cached = await repo.find_by_date_range(from_date, to_date, procedure_filter)

    rows: list[ScheduleExportRow | EnrichedExportRow] = []
    for entry in cached:
        try:
            data = entry.row_data
            has_enrichment = any(data.get(f) for f in ("cpf_paciente", "telefone_cadsus", "email_paciente"))
            row = EnrichedExportRow(**data) if has_enrichment else ScheduleExportRow(**data)
            rows.append(row)
        except Exception:
            logger.warning("Failed to deserialize cached row solicitacao=%s, skipping", entry.solicitacao)

    logger.info("Cache query: %d rows loaded from DB (date range %s to %s)", len(rows), date_from, date_to)
    return rows


async def persist_export_rows(
    rows: list[ScheduleExportRow | EnrichedExportRow],
    db_session: AsyncSession,
) -> int:
    """Upsert export rows (raw or enriched) to cache table. Returns count persisted."""
    if not rows:
        return 0

    repo = CachedExportRepository(db_session)
    dicts: list[dict] = []
    for row in rows:
        if not row.solicitacao:
            continue
        dicts.append({
            "solicitacao": row.solicitacao,
            "data_agendamento": row.data_agendamento,
            "data_agendamento_iso": _parse_date_ddmmyyyy(row.data_agendamento),
            "descricao_procedimento": row.descricao_procedimento,
            "row_data": row.model_dump(),
        })

    if not dicts:
        return 0

    count = await repo.bulk_upsert(dicts)
    await db_session.commit()

    logger.info("Cache persist: %d rows upserted to DB", count)
    return count


async def enrich_rows_with_cadsus(
    rows: list[ScheduleExportRow],
    procedure_filter: str | None = None,
) -> list[EnrichedExportRow]:
    """Filter rows by procedure and enrich with CADSUS data.

    1. Filter by descricao_procedimento (case-insensitive contains) if filter given
    2. Extract unique CNS from filtered rows
    3. Look up CADSUS in parallel with semaphore rate limiting
    4. Merge CADSUS data into enriched rows
    """
    from regulahub.config import get_cadsus_settings
    from regulahub.integrations.cadsus_client import CadsusClient, CadsusPatientData

    settings = get_cadsus_settings()
    if not settings.cadsus_enabled:
        logger.info("CADSUS enrichment disabled, returning rows as-is")
        return [EnrichedExportRow(**row.model_dump()) for row in rows]

    # Filter by procedure if specified (already done in route, but defensive)
    if procedure_filter:
        filter_lower = procedure_filter.lower()
        filtered = [r for r in rows if filter_lower in r.descricao_procedimento.lower()]
    else:
        filtered = list(rows)

    if not filtered:
        return []

    # Extract unique CNS values
    unique_cns = {r.cns for r in filtered if r.cns}
    logger.info("CADSUS enrichment: %d unique CNS to look up from %d rows", len(unique_cns), len(filtered))

    # Look up CADSUS in parallel
    client = CadsusClient(settings=settings)
    semaphore = asyncio.Semaphore(10)
    cache: dict[str, CadsusPatientData | None] = {}

    async def _lookup(cns: str) -> tuple[str, CadsusPatientData | None]:
        async with semaphore:
            result = await client.get_patient_by_cns(cns)
            return cns, result

    tasks = [_lookup(cns) for cns in unique_cns]
    results = await asyncio.gather(*tasks)
    for cns, patient_data in results:
        cache[cns] = patient_data

    # Build enriched rows
    enriched: list[EnrichedExportRow] = []
    for row in filtered:
        patient = cache.get(row.cns) if row.cns else None
        enriched_row = EnrichedExportRow(
            **row.model_dump(),
            cpf_paciente=patient.cpf if patient else None,
            email_paciente=patient.email if patient else None,
            telefone_cadsus=patient.phone if patient else None,
            nome_pai=patient.father_name if patient else None,
            raca=patient.race if patient else None,
            cns_definitivo=patient.cns if patient else None,
        )
        enriched.append(enriched_row)

    enriched_count = sum(1 for p in cache.values() if p and p.cpf)
    logger.info("CADSUS enrichment: %d/%d CNS resolved with CPF", enriched_count, len(unique_cns))

    return enriched
