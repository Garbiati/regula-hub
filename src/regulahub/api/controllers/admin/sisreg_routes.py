"""Admin endpoints for SisReg appointment queries."""

import asyncio
import io
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.api.deps import verify_api_key
from regulahub.api.rate_limit import limiter
from regulahub.db.engine import get_session
from regulahub.services.credential_service import CredentialNotFoundError, resolve_credential_by_username
from regulahub.sisreg.client import SisregClient, SisregLoginError
from regulahub.sisreg.models import (
    AppointmentDetail,
    AppointmentListing,
    OperatorSearchResponse,
    SearchFilters,
    SearchResponse,
)
from regulahub.utils.masking import mask_username

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/sisreg", tags=["admin-sisreg"], dependencies=[Depends(verify_api_key)])

SISREG_BASE_URL = "https://sisregiii.saude.gov.br"


async def _search_single_operator(
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
            logger.info("Operator %s returned %d items", user_hash, len(result.items))
            return result.items
    except SisregLoginError:
        logger.warning("SisReg login failed for operator %s, skipping", user_hash)
        return []
    except Exception:
        logger.exception("SisReg search error for operator %s, skipping", user_hash)
        return []


@router.post("/search", response_model=SearchResponse)
@limiter.limit("10/minute")
async def search_appointments(
    request: Request,
    filters: SearchFilters,
    db: AsyncSession = Depends(get_session),
) -> SearchResponse:
    """Search SisReg appointments. For multi-operator profiles, searches in parallel and merges results."""
    # Resolve credentials for all requested usernames
    credentials: list[tuple[str, str]] = []
    for uname in filters.usernames:
        try:
            cred = await resolve_credential_by_username(
                system="SISREG",
                profile_type=filters.profile_type,
                username=uname,
                db_session=db,
            )
            credentials.append(cred)
        except CredentialNotFoundError:
            logger.warning("No credential found for username %s, skipping", mask_username(uname))

    if not credentials:
        raise HTTPException(status_code=404, detail="No valid credentials found for the given usernames")

    # Single operator — direct search
    if len(credentials) == 1:
        username, password = credentials[0]
        user_hash = mask_username(username)
        try:
            async with SisregClient(SISREG_BASE_URL, username, password, filters.profile_type) as client:
                return await client.search(filters)
        except SisregLoginError:
            logger.error("SisReg login failed for user %s", user_hash)
            raise HTTPException(status_code=502, detail="SisReg login failed") from None
        except Exception:
            logger.exception("SisReg search error for user %s", user_hash)
            raise HTTPException(status_code=502, detail="SisReg search failed") from None

    # Multiple operators — parallel search and merge
    tasks = [
        _search_single_operator(username, password, filters.profile_type, filters) for username, password in credentials
    ]
    results = await asyncio.gather(*tasks)

    # Merge and deduplicate by solicitation code
    seen_codes: set[str] = set()
    merged: list[AppointmentListing] = []
    for items in results:
        for item in items:
            if item.code not in seen_codes:
                seen_codes.add(item.code)
                merged.append(item)

    logger.info("Parallel search: %d operators, %d unique items", len(credentials), len(merged))
    return SearchResponse(items=merged, total=len(merged))


@router.get("/{code}/detail", response_model=AppointmentDetail)
@limiter.limit("20/minute")
async def get_appointment_detail(
    request: Request,
    code: str,
    username: str,
    profile_type: str = "VIDEOFONISTA",
    db: AsyncSession = Depends(get_session),
) -> AppointmentDetail:
    """Get appointment detail by solicitation code."""
    try:
        resolved_username, password = await resolve_credential_by_username(
            system="SISREG",
            profile_type=profile_type,
            username=username,
            db_session=db,
        )
    except CredentialNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    user_hash = mask_username(resolved_username)

    try:
        async with SisregClient(SISREG_BASE_URL, resolved_username, password, profile_type) as client:
            return await client.detail(code)
    except SisregLoginError:
        logger.error("SisReg login failed for user %s", user_hash)
        raise HTTPException(status_code=502, detail="SisReg login failed") from None
    except Exception:
        logger.exception("SisReg detail error for code %s, user %s", code, user_hash)
        raise HTTPException(status_code=502, detail="SisReg detail fetch failed") from None


@router.post("/search-operator", response_model=OperatorSearchResponse)
@limiter.limit("30/minute")
async def search_single_operator_endpoint(
    request: Request,
    filters: SearchFilters,
    db: AsyncSession = Depends(get_session),
) -> OperatorSearchResponse:
    """Search SisReg with exactly one operator. Used by the pipeline visualization to track per-operator progress."""
    if len(filters.usernames) != 1:
        raise HTTPException(status_code=422, detail="Exactly one username is required for single-operator search")

    username = filters.usernames[0]
    try:
        resolved_username, password = await resolve_credential_by_username(
            system="SISREG",
            profile_type=filters.profile_type,
            username=username,
            db_session=db,
        )
    except CredentialNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    user_hash = mask_username(resolved_username)
    try:
        async with SisregClient(SISREG_BASE_URL, resolved_username, password, filters.profile_type) as client:
            result = await client.search(filters)
            logger.info("Single-operator search: %s returned %d items", user_hash, len(result.items))
            return OperatorSearchResponse(operator=username, items=result.items, total=result.total)
    except SisregLoginError:
        logger.error("SisReg login failed for user %s", user_hash)
        raise HTTPException(status_code=502, detail="SisReg login failed") from None
    except Exception:
        logger.exception("SisReg search error for user %s", user_hash)
        raise HTTPException(status_code=502, detail="SisReg search failed") from None


@router.post("/export")
@limiter.limit("5/minute")
async def export_appointments(
    request: Request,
    filters: SearchFilters,
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Export SisReg appointments as CSV. Supports multi-operator parallel search."""
    # Resolve credentials for all requested usernames
    credentials: list[tuple[str, str]] = []
    for uname in filters.usernames:
        try:
            cred = await resolve_credential_by_username(
                system="SISREG",
                profile_type=filters.profile_type,
                username=uname,
                db_session=db,
            )
            credentials.append(cred)
        except CredentialNotFoundError:
            logger.warning("No credential found for username %s, skipping", mask_username(uname))

    if not credentials:
        raise HTTPException(status_code=404, detail="No valid credentials found for the given usernames")

    # Search (single or parallel)
    if len(credentials) == 1:
        username, password = credentials[0]
        user_hash = mask_username(username)
        try:
            async with SisregClient(SISREG_BASE_URL, username, password, filters.profile_type) as client:
                result = await client.search(filters)
        except SisregLoginError:
            logger.error("SisReg login failed for export, user %s", user_hash)
            raise HTTPException(status_code=502, detail="SisReg login failed") from None
        except Exception:
            logger.exception("SisReg export error for user %s", user_hash)
            raise HTTPException(status_code=502, detail="SisReg export failed") from None
        items = result.items
    else:
        tasks = [
            _search_single_operator(username, password, filters.profile_type, filters)
            for username, password in credentials
        ]
        results = await asyncio.gather(*tasks)
        seen_codes: set[str] = set()
        items = []
        for batch in results:
            for item in batch:
                if item.code not in seen_codes:
                    seen_codes.add(item.code)
                    items.append(item)

    # Build CSV
    buf = io.StringIO()
    headers = [
        "code",
        "request_date",
        "risk",
        "patient_name",
        "phone",
        "municipality",
        "age",
        "procedure",
        "cid",
        "dept_solicitation",
        "dept_execute",
        "execution_date",
        "status",
    ]
    buf.write(",".join(headers) + "\n")
    for item in items:
        row = [
            item.code,
            item.request_date,
            str(item.risk),
            item.patient_name,
            item.phone,
            item.municipality,
            item.age,
            item.procedure,
            item.cid,
            item.dept_solicitation,
            item.dept_execute,
            item.execution_date,
            item.status,
        ]
        # Escape CSV fields
        escaped = []
        for field in row:
            if "," in field or '"' in field or "\n" in field:
                escaped.append('"' + field.replace('"', '""') + '"')
            else:
                escaped.append(field)
        buf.write(",".join(escaped) + "\n")

    buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005
    filename = f"sisreg_export_{timestamp}.csv"

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
