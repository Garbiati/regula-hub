import importlib.metadata
import logging
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from regulahub.api.schemas import DependencyCheck, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()

_VERSION = importlib.metadata.version("regula-hub")


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse | JSONResponse:
    uptime = time.monotonic() - request.app.state.startup_time
    timestamp = datetime.now(UTC).isoformat()

    db_check = await _check_database()
    fernet_check = _check_fernet()

    checks = {
        "database": db_check,
        "encryption": fernet_check,
    }

    overall = "healthy" if all(c.status == "healthy" for c in checks.values()) else "unhealthy"

    response = HealthResponse(
        status=overall,
        version=_VERSION,
        uptime_seconds=round(uptime, 2),
        timestamp=timestamp,
        checks=checks,
    )

    if overall == "unhealthy":
        return JSONResponse(status_code=503, content=response.model_dump())

    return response


async def _check_database() -> DependencyCheck:
    """Check database connectivity with a simple SELECT 1 query."""
    try:
        from regulahub.db.engine import get_engine

        engine = get_engine()
        start = time.monotonic()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = round((time.monotonic() - start) * 1000, 2)
        return DependencyCheck(status="healthy", latency_ms=latency)
    except Exception:
        logger.exception("Database health check failed")
        return DependencyCheck(status="unhealthy", detail="Database unavailable")


def _check_fernet() -> DependencyCheck:
    """Verify the Fernet encryption key is valid and usable."""
    try:
        from regulahub.utils.encryption import encrypt_password

        encrypt_password("healthcheck")
        return DependencyCheck(status="healthy")
    except Exception:
        logger.exception("Fernet encryption key check failed")
        return DependencyCheck(status="unhealthy", detail="Encryption key invalid")
