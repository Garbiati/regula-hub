import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from regulahub.api.controllers.admin.credential_routes import router as credential_router
from regulahub.api.controllers.admin.integration_appointment_routes import router as integration_appointment_router
from regulahub.api.controllers.admin.integration_appointment_routes import webhook_router as discharge_webhook_router
from regulahub.api.controllers.admin.integration_routes import router as integration_router
from regulahub.api.controllers.admin.regulation_system_routes import router as regulation_system_router
from regulahub.api.controllers.admin.routes import router as admin_router
from regulahub.api.controllers.admin.schedule_export_routes import router as schedule_export_router
from regulahub.api.controllers.admin.sisreg_routes import router as sisreg_router
from regulahub.api.controllers.admin.user_routes import router as user_router
from regulahub.api.controllers.compat.absens_routes import router as compat_absens_router
from regulahub.api.rate_limit import limiter
from regulahub.api.routes import router
from regulahub.config import get_settings
from regulahub.logging_config import setup_logging

logger = logging.getLogger(__name__)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.startup_time = time.monotonic()

    # Start pipeline background jobs (fetch → enrich → push)
    from regulahub.services.integration_worker_service import start_pipeline_jobs

    try:
        await start_pipeline_jobs()
    except Exception:
        logger.exception("Failed to start pipeline jobs — pipeline will not run")

    yield

    from regulahub.db.engine import dispose_engine

    await dispose_engine()


app = FastAPI(
    title="RegulaHub",
    description="Integration platform for Brazilian regulation systems",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins.split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type", "Accept", "Authorization", "X-Request-ID"],
)


@app.middleware("http")
async def request_id_and_logging_middleware(request: Request, call_next):  # noqa: ANN001
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start = time.monotonic()
    response = await call_next(request)
    latency_ms = round((time.monotonic() - start) * 1000, 2)

    logger.info(
        "Request completed: %s %s -> %s (%.2fms)",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )

    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):  # noqa: ANN001
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(router)
app.include_router(admin_router)
app.include_router(credential_router)
app.include_router(regulation_system_router)
app.include_router(sisreg_router)
app.include_router(schedule_export_router)
app.include_router(user_router)
app.include_router(integration_router)
app.include_router(integration_appointment_router)
app.include_router(discharge_webhook_router)
app.include_router(compat_absens_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    client_ip = request.client.host if request.client else "unknown"
    logger.exception(
        "Unhandled exception on %s %s from %s",
        request.method,
        request.url.path,
        client_ip,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
