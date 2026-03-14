"""Absens-compatible service layer — maps SisReg data to the Absens JSON contract."""

import asyncio
import dataclasses
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.api.controllers.compat.absens_schemas import (
    AbsensAppointmentResponse,
    AbsensDetailResponse,
    DepartmentSolicitationInfosResponse,
    PatientPhoneResponse,
)
from regulahub.db.repositories.credential import CredentialRepository
from regulahub.services.credential_service import CredentialNotFoundError, resolve_single_credential
from regulahub.sisreg.client import SisregClient, SisregLoginError
from regulahub.sisreg.models import AppointmentDetail, AppointmentListing, BestPhone, CadwebPatientData, SearchFilters
from regulahub.utils.encryption import decrypt_password
from regulahub.utils.masking import mask_username

logger = logging.getLogger(__name__)

SISREG_BASE_URL = "https://sisregiii.saude.gov.br"

_WEEKDAY_PT_BR = {
    0: "SEG",
    1: "TER",
    2: "QUA",
    3: "QUI",
    4: "SEX",
    5: "SAB",
    6: "DOM",
}


def format_appointment_date(raw_date: str | None) -> str:
    """Convert SisReg date to the '● dd/MM/yyyy ● HHhMMmin' format expected by regulation-service.

    Rules:
    - None/empty → ""
    - Already contains ● → passthrough
    - dd/MM/yyyy → "DIA ● dd/MM/yyyy ● 00h00min"
    - dd/MM/yyyy HH:mm → "DIA ● dd/MM/yyyy ● HHhMMmin"
    """
    if not raw_date or not raw_date.strip():
        return ""

    raw_date = raw_date.strip()

    if "●" in raw_date:
        return raw_date

    # Try dd/MM/yyyy HH:mm
    parts = raw_date.split(" ", 1)
    date_part = parts[0]

    try:
        dt = datetime.strptime(date_part, "%d/%m/%Y")  # noqa: DTZ007
    except ValueError:
        logger.warning("Unparseable appointment date: %s", raw_date)
        return ""

    weekday = _WEEKDAY_PT_BR[dt.weekday()]

    if len(parts) == 2:
        time_part = parts[1].strip()
        try:
            time_dt = datetime.strptime(time_part, "%H:%M")  # noqa: DTZ007
            time_str = f"{time_dt.hour:02d}h{time_dt.minute:02d}min"
        except ValueError:
            time_str = "00h00min"
    else:
        time_str = "00h00min"

    return f"{weekday} ● {date_part} ● {time_str}"


@dataclasses.dataclass
class EnrichmentData:
    """Combined enrichment data from fichaAmbulatorial + CadWeb."""

    detail: AppointmentDetail
    cadweb: CadwebPatientData | None = None


def _map_phone(phone: BestPhone | None) -> PatientPhoneResponse | None:
    """Map BestPhone to PatientPhoneResponse."""
    if phone is None:
        return None
    return PatientPhoneResponse(ddd=phone.ddd, number=phone.number)


def map_listing_to_absens(
    listing: AppointmentListing,
    enrichment: EnrichmentData | None = None,
) -> AbsensAppointmentResponse:
    """Map a SisReg AppointmentListing to the Absens AppointmentDTO contract."""
    birth_date = ""
    mother_name = ""
    if enrichment:
        birth_date = enrichment.detail.patient_birth_date or ""
        if enrichment.cadweb:
            mother_name = enrichment.cadweb.mother_name or ""

    return AbsensAppointmentResponse(
        cod=listing.code,
        department_execute=listing.dept_execute,
        department_solicitation=listing.dept_solicitation,
        procedure=listing.procedure,
        status_sisreg=listing.status or None,  # Convert empty string "" to None (spec: nullable field)
        patient_birthday=birth_date,
        patient_mother_name=mother_name,
    )


def map_detail_to_absens(
    detail: AppointmentDetail,
    code: str,
    cadweb: CadwebPatientData | None = None,
) -> AbsensDetailResponse:
    """Map a SisReg AppointmentDetail to the Absens DetailsAppointmentDTO contract."""
    # Phone: prefer CadWeb CELULAR over fichaAmbulatorial phone
    if cadweb and cadweb.phone_ddd and cadweb.phone_number:
        best_phone = PatientPhoneResponse(ddd=cadweb.phone_ddd, number=cadweb.phone_number)
    else:
        best_phone = _map_phone(detail.best_phone)

    patient_phones = [best_phone] if best_phone else None
    patient_cpf = cadweb.cpf if cadweb else None

    dept_sol_infos = None
    if detail.req_unit_cnes or detail.req_unit_name:
        dept_sol_infos = DepartmentSolicitationInfosResponse(
            cnes=detail.req_unit_cnes or "",
            department=detail.req_unit_name or "",
        )

    return AbsensDetailResponse(
        cod=detail.sol_code or code,
        confirmation_key=detail.confirmation_key or "",
        patient=detail.patient_name or "",
        patient_cpf=patient_cpf,
        cns=detail.patient_cns or "",
        patient_phones=patient_phones,
        department_solicitation=detail.req_unit_name or "",
        department_execute=detail.department or "",
        appointment_date=format_appointment_date(detail.appointment_date),
        status_sisreg=detail.sol_status or "",
        doctor_execute=detail.doctor_name or "",
        best_phone=best_phone,
        department_solicitation_infos=dept_sol_infos,
    )


async def _fetch_details_for_codes(
    codes: list[str],
    username: str,
    password: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, EnrichmentData]:
    """Fetch detail + CadWeb data for a batch of codes using a single SisReg session."""
    result: dict[str, EnrichmentData] = {}
    user_hash = mask_username(username)
    cadweb_cache: dict[str, CadwebPatientData | None] = {}

    async with semaphore:
        try:
            async with SisregClient(SISREG_BASE_URL, username, password, "VIDEOFONISTA") as client:
                for code in codes:
                    try:
                        detail = await client.detail(code)

                        # CadWeb lookup by CNS (with cache to avoid duplicate queries)
                        cadweb = None
                        cns = detail.patient_cns
                        if cns:
                            if cns in cadweb_cache:
                                cadweb = cadweb_cache[cns]
                            else:
                                try:
                                    cadweb = await client.cadweb_lookup(cns)
                                except Exception:
                                    logger.warning("CadWeb lookup failed for code %s (operator %s)", code, user_hash)
                                cadweb_cache[cns] = cadweb

                        result[code] = EnrichmentData(detail=detail, cadweb=cadweb)
                    except Exception:
                        logger.warning("Enrichment failed for code %s (operator %s)", code, user_hash)
        except SisregLoginError:
            logger.warning("Enrichment login failed for operator %s, skipping %d codes", user_hash, len(codes))
        except Exception:
            logger.exception("Enrichment session error for operator %s", user_hash)

    return result


async def _enrich_listings(
    listings: list[AppointmentListing],
    credentials: list[tuple[str, str]],
) -> dict[str, EnrichmentData]:
    """Enrich listings with detail + CadWeb data via parallel SisReg sessions."""
    if not listings:
        return {}

    codes = [item.code for item in listings]
    semaphore = asyncio.Semaphore(5)

    # Round-robin distribution across credentials
    batches: dict[int, list[str]] = {i: [] for i in range(len(credentials))}
    for idx, code in enumerate(codes):
        batches[idx % len(credentials)].append(code)

    tasks = [
        _fetch_details_for_codes(batch_codes, credentials[cred_idx][0], credentials[cred_idx][1], semaphore)
        for cred_idx, batch_codes in batches.items()
        if batch_codes
    ]

    results = await asyncio.gather(*tasks)

    merged: dict[str, EnrichmentData] = {}
    for result_dict in results:
        merged.update(result_dict)

    enriched_count = sum(1 for v in merged.values() if v.detail.patient_birth_date)
    logger.info("Enrichment: %d/%d codes enriched", enriched_count, len(codes))
    return merged


async def _search_single_operator_compat(
    username: str,
    password: str,
    profile_type: str,
    filters: SearchFilters,
) -> list[AppointmentListing]:
    """Search SisReg with a single operator credential, returning items or empty on failure."""
    user_hash = mask_username(username)
    try:
        async with SisregClient(SISREG_BASE_URL, username, password, profile_type) as client:
            result = await client.search(filters)
            logger.info("Compat operator %s returned %d items", user_hash, len(result.items))
            return result.items
    except SisregLoginError:
        logger.warning("Compat SisReg login failed for operator %s, skipping", user_hash)
        return []
    except Exception:
        logger.exception("Compat SisReg search error for operator %s, skipping", user_hash)
        return []


async def _resolve_all_credentials(
    db_session: AsyncSession,
) -> list[tuple[str, str]]:
    """Resolve all active VIDEOFONISTA credentials for SISREG."""
    repo = CredentialRepository(db_session)
    creds = await repo.get_active_by_system_and_profile("SISREG", "VIDEOFONISTA")

    if not creds:
        raise CredentialNotFoundError("No VIDEOFONISTA credentials configured for SISREG")

    resolved: list[tuple[str, str]] = []
    for cred in creds:
        try:
            pw = decrypt_password(cred.encrypted_password)
            resolved.append((cred.username, pw))
        except ValueError:
            logger.warning("Failed to decrypt credential for operator %s, skipping", mask_username(cred.username))

    if not resolved:
        raise CredentialNotFoundError("All VIDEOFONISTA credentials failed decryption")

    return resolved


async def fetch_appointments(date_str: str, db_session: AsyncSession) -> list[AbsensAppointmentResponse]:
    """Fetch appointments for a date from SisReg using all VIDEOFONISTA credentials in parallel.

    Args:
        date_str: Date in YYYY-MM-DD format.
        db_session: Async database session.

    Returns:
        Deduplicated list of AbsensAppointmentResponse.
    """
    credentials = await _resolve_all_credentials(db_session)

    # Convert YYYY-MM-DD to dd/MM/yyyy
    dt = datetime.strptime(date_str, "%Y-%m-%d")  # noqa: DTZ007
    date_br = dt.strftime("%d/%m/%Y")

    # Build filters — filter teleconsulta at SisReg level (ds_procedimento + situation 7)
    # to avoid fetching thousands of non-teleconsulta appointments
    base_filters = SearchFilters(
        date_from=date_br,
        date_to=date_br,
        procedure_description="teleconsulta",
        situation="7",
        profile_type="VIDEOFONISTA",
        usernames=[credentials[0][0]],
    )

    # Parallel search across all credentials
    tasks = [
        _search_single_operator_compat(username, password, "VIDEOFONISTA", base_filters)
        for username, password in credentials
    ]
    results = await asyncio.gather(*tasks)

    # Merge and deduplicate by code
    seen_codes: set[str] = set()
    merged: list[AppointmentListing] = []
    for items in results:
        for item in items:
            if item.code not in seen_codes:
                seen_codes.add(item.code)
                merged.append(item)

    logger.info("Compat fetch_appointments: %d operators, %d teleconsulta items", len(credentials), len(merged))

    # Enrich with detail + CadWeb data
    enrichment = await _enrich_listings(merged, credentials)

    return [map_listing_to_absens(item, enrichment=enrichment.get(item.code)) for item in merged]


async def fetch_detail(code: str, db_session: AsyncSession) -> AbsensDetailResponse:
    """Fetch appointment detail from SisReg using the first available VIDEOFONISTA credential.

    Args:
        code: Solicitation code.
        db_session: Async database session.

    Returns:
        AbsensDetailResponse mapped from SisReg detail.
    """
    username, password = await resolve_single_credential("SISREG", "VIDEOFONISTA", db_session=db_session)
    user_hash = mask_username(username)

    try:
        async with SisregClient(SISREG_BASE_URL, username, password, "VIDEOFONISTA") as client:
            detail = await client.detail(code)

            # CadWeb enrichment
            cadweb = None
            if detail.patient_cns:
                try:
                    cadweb = await client.cadweb_lookup(detail.patient_cns)
                except Exception:
                    logger.warning("CadWeb lookup failed for code %s", code)
    except SisregLoginError:
        logger.error("Compat SisReg login failed for user %s on detail %s", user_hash, code)
        raise
    except Exception:
        logger.exception("Compat SisReg detail error for code %s, user %s", code, user_hash)
        raise

    return map_detail_to_absens(detail, code, cadweb=cadweb)
