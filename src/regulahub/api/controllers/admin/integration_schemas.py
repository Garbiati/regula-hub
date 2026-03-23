"""Pydantic schemas for integration worker endpoints."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Request schemas ──────────────────────────────────────────────────────


class TriggerExecutionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    system_code: str = Field(
        ..., validation_alias="systemCode", min_length=1, max_length=30, description="Integration system code"
    )
    date_from: date = Field(..., validation_alias="dateFrom", description="Start date (YYYY-MM-DD)")
    date_to: date = Field(..., validation_alias="dateTo", description="End date (YYYY-MM-DD)")


# ── Response schemas ─────────────────────────────────────────────────────


class IntegrationEndpointResponse(BaseModel):
    id: uuid.UUID
    name: str
    protocol: str
    http_method: str | None = None
    path: str
    description: str | None = None
    is_active: bool


class IntegrationSystemResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    base_url: str | None = None
    category: str | None = None
    state: str | None = None
    state_name: str | None = None
    endpoints: list[IntegrationEndpointResponse] = []


class IntegrationSystemListResponse(BaseModel):
    items: list[IntegrationSystemResponse]
    total: int


class IntegrationProgressResponse(BaseModel):
    stage: str = ""
    fetched_count: int = 0
    enriched_count: int = 0
    pushed_count: int = 0
    failed_count: int = 0


class ExecutionStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    date_from: date
    date_to: date
    total_fetched: int | None = None
    total_enriched: int | None = None
    total_pushed: int | None = None
    total_failed: int | None = None
    error_message: str | None = None
    progress_data: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    triggered_by: str | None = None
    created_at: datetime | None = None


class ExecutionListResponse(BaseModel):
    items: list[ExecutionStatusResponse]
    total: int
