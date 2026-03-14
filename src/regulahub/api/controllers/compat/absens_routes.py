"""Absens-compatible API endpoints — drop-in replacement for regulation-service migration."""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.api.controllers.compat.absens_auth import verify_compat_auth
from regulahub.api.rate_limit import limiter
from regulahub.db.engine import get_session
from regulahub.services.compat_service import fetch_appointments, fetch_detail
from regulahub.services.credential_service import CredentialNotFoundError
from regulahub.sisreg.client import SisregLoginError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/compat/absens",
    tags=["compat-absens"],
    dependencies=[Depends(verify_compat_auth)],
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.get("/agendamentos")
@limiter.limit("200/minute")
async def get_agendamentos(
    request: Request,
    date: str | None = Query(default=None, description="Date in YYYY-MM-DD format", min_length=10, max_length=10),
    codigo: str | None = Query(default=None, description="Solicitation code", min_length=1, max_length=50),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Absens-compatible endpoint for appointments (listing by date or detail by code)."""
    if date and codigo:
        raise HTTPException(status_code=422, detail="Parameters 'date' and 'codigo' are mutually exclusive")
    if not date and not codigo:
        raise HTTPException(status_code=422, detail="Either 'date' or 'codigo' parameter is required")

    if date:
        if not _DATE_PATTERN.match(date):
            raise HTTPException(status_code=422, detail="Parameter 'date' must be in YYYY-MM-DD format")
        try:
            datetime.strptime(date, "%Y-%m-%d")  # noqa: DTZ007
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid calendar date") from None
        try:
            results = await fetch_appointments(date, db)
        except CredentialNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception:
            logger.exception("Compat appointment fetch error for date %s", date)
            raise HTTPException(status_code=502, detail="SisReg search failed") from None
        return JSONResponse(content=[r.model_dump(by_alias=True) for r in results])

    # codigo path
    try:
        result = await fetch_detail(codigo, db)
    except CredentialNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SisregLoginError:
        raise HTTPException(status_code=502, detail="SisReg login failed") from None
    except Exception:
        logger.exception("Compat detail fetch error for code %s", codigo)
        raise HTTPException(status_code=502, detail="SisReg detail fetch failed") from None
    return JSONResponse(content=result.model_dump(by_alias=True))


@router.get("/cancelamentos")
@limiter.limit("200/minute")
async def get_cancelamentos(
    request: Request,
    date: str | None = Query(default=None, description="Date in YYYY-MM-DD format"),
) -> JSONResponse:
    """Absens-compatible endpoint for cancellations — always returns empty list."""
    return JSONResponse(content=[])
