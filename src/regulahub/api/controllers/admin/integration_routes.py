"""Admin routes for integration worker management."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.api.controllers.admin.integration_schemas import (
    ExecutionListResponse,
    ExecutionStatusResponse,
    IntegrationEndpointResponse,
    IntegrationSystemListResponse,
    IntegrationSystemResponse,
    TriggerExecutionRequest,
)
from regulahub.api.deps import verify_api_key
from regulahub.api.rate_limit import limiter
from regulahub.db.engine import get_session
from regulahub.db.repositories.integration_execution import IntegrationExecutionRepository
from regulahub.db.repositories.regulation_system import RegulationSystemRepository
from regulahub.services.integration_worker_service import (
    cancel_execution,
    get_execution_progress,
    trigger_execution,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/integrations",
    tags=["admin-integrations"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/systems", response_model=IntegrationSystemListResponse)
@limiter.limit("30/minute")
async def list_integration_systems(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> IntegrationSystemListResponse:
    """List configured integration systems with their endpoints."""
    repo = RegulationSystemRepository(db)
    systems = await repo.list_integration_systems()

    items = []
    for system in systems:
        endpoints = await repo.get_endpoints_for_system(system.id)
        items.append(
            IntegrationSystemResponse(
                id=system.id,
                code=system.code,
                name=system.name,
                description=system.description,
                base_url=system.base_url,
                category=system.category,
                state=system.state,
                state_name=system.state_name,
                endpoints=[
                    IntegrationEndpointResponse(
                        id=ep.id,
                        name=ep.name,
                        protocol=ep.protocol,
                        http_method=ep.http_method,
                        path=ep.path,
                        description=ep.description,
                        is_active=ep.is_active,
                    )
                    for ep in endpoints
                ],
            )
        )

    return IntegrationSystemListResponse(items=items, total=len(items))


@router.post("/execute", response_model=ExecutionStatusResponse, status_code=202)
@limiter.limit("3/minute")
async def trigger_worker_execution(
    request: Request,
    body: TriggerExecutionRequest,
    db: AsyncSession = Depends(get_session),
) -> ExecutionStatusResponse:
    """Trigger a new integration worker execution. Returns 202 Accepted with execution ID."""
    if body.date_from > body.date_to:
        raise HTTPException(status_code=422, detail="date_from must be before or equal to date_to")

    try:
        execution_id = await trigger_execution(
            system_code=body.system_code,
            date_from=body.date_from,
            date_to=body.date_to,
            db_session=db,
            triggered_by="manual",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        error_msg = str(exc)
        if "already running" in error_msg:
            raise HTTPException(status_code=409, detail=error_msg) from exc
        raise HTTPException(status_code=503, detail=error_msg) from exc

    return ExecutionStatusResponse(
        id=execution_id,
        status="pending",
        date_from=body.date_from,
        date_to=body.date_to,
    )


@router.get("/executions/{execution_id}/status", response_model=ExecutionStatusResponse)
@limiter.limit("60/minute")
async def get_execution_status(
    request: Request,
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> ExecutionStatusResponse:
    """Get execution status. Checks in-memory first, then DB fallback."""
    # Check in-memory progress first (for live status)
    progress = get_execution_progress(execution_id)
    if progress:
        return ExecutionStatusResponse(
            id=execution_id,
            status=progress.status,
            date_from=progress.date_from,
            date_to=progress.date_to,
            total_fetched=progress.total_fetched,
            total_enriched=progress.total_enriched,
            total_pushed=progress.total_pushed,
            total_failed=progress.total_failed,
            error_message=progress.error_message,
            progress_data=progress.to_dict(),
            started_at=progress.started_at,
            completed_at=progress.completed_at,
        )

    # Fallback to DB
    repo = IntegrationExecutionRepository(db)
    execution = await repo.get_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return ExecutionStatusResponse(
        id=execution.id,
        status=execution.status,
        date_from=execution.date_from,
        date_to=execution.date_to,
        total_fetched=execution.total_fetched,
        total_enriched=execution.total_enriched,
        total_pushed=execution.total_pushed,
        total_failed=execution.total_failed,
        error_message=execution.error_message,
        progress_data=execution.progress_data,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        triggered_by=execution.triggered_by,
        created_at=execution.created_at,
    )


@router.get("/executions", response_model=ExecutionListResponse)
@limiter.limit("30/minute")
async def list_executions(
    request: Request,
    system_code: str | None = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_session),
) -> ExecutionListResponse:
    """List execution history with pagination. Optionally filter by system code."""
    repo = IntegrationExecutionRepository(db)

    if system_code:
        sys_repo = RegulationSystemRepository(db)
        system = await sys_repo.get_by_code(system_code)
        if not system:
            raise HTTPException(status_code=404, detail=f"System '{system_code}' not found")
        items, total = await repo.list_by_system(system.id, skip=skip, limit=limit)
    else:
        items, total = await repo.list_all(skip=skip, limit=limit)

    return ExecutionListResponse(
        items=[
            ExecutionStatusResponse(
                id=ex.id,
                status=ex.status,
                date_from=ex.date_from,
                date_to=ex.date_to,
                total_fetched=ex.total_fetched,
                total_enriched=ex.total_enriched,
                total_pushed=ex.total_pushed,
                total_failed=ex.total_failed,
                error_message=ex.error_message,
                progress_data=ex.progress_data,
                started_at=ex.started_at,
                completed_at=ex.completed_at,
                triggered_by=ex.triggered_by,
                created_at=ex.created_at,
            )
            for ex in items
        ],
        total=total,
    )


@router.post("/executions/{execution_id}/cancel")
@limiter.limit("5/minute")
async def cancel_worker_execution(
    request: Request,
    execution_id: uuid.UUID,
) -> dict:
    """Cancel a running execution."""
    cancelled = cancel_execution(execution_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Execution not found or not running")
    return {"id": str(execution_id), "status": "cancelling"}
