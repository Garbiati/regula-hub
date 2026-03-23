"""Pydantic schemas for integration appointment endpoints."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

# ── Request schemas ──────────────────────────────────────────────────────


class AppointmentListRequest(BaseModel):
    """Query parameters for listing appointments."""

    status: str | None = Field(None, description="Filter by appointment status")
    date_from: date | None = Field(None, description="Filter appointments from this date (inclusive)")
    date_to: date | None = Field(None, description="Filter appointments up to this date (inclusive)")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of records to return")


class AppointmentUpdateRequest(BaseModel):
    """Partial update for appointment data (only non-None fields are applied)."""

    patient_name: str | None = None
    patient_cpf: str | None = None
    patient_cns: str | None = None
    patient_birth_date: str | None = None
    patient_phone: str | None = None
    doctor_name: str | None = None
    doctor_cpf: str | None = None
    department_executor: str | None = None
    department_executor_cnes: str | None = None


class DischargeWebhookRequest(BaseModel):
    """Webhook payload from external systems to report appointment discharge."""

    external_id: str = Field(..., min_length=1, description="External appointment identifier")
    status: str = Field(..., pattern="^(completed|no_show)$", description="Discharge status: completed or no_show")
    discharged_at: datetime | None = Field(None, description="Timestamp of discharge")
    doctor_id: str | None = Field(None, description="Identifier of the discharging doctor")
    notes: str | None = Field(None, description="Additional discharge notes")


# ── Response schemas ─────────────────────────────────────────────────────


class AppointmentResponse(BaseModel):
    """Single appointment record."""

    id: uuid.UUID
    integration_system_id: uuid.UUID
    execution_id: uuid.UUID | None = None
    regulation_code: str
    confirmation_key: str | None = None
    external_id: str | None = None
    patient_name: str
    patient_cpf: str | None = None
    patient_cns: str | None = None
    patient_birth_date: str | None = None
    patient_phone: str | None = None
    patient_mother_name: str | None = None
    appointment_date: date
    appointment_time: str | None = None  # HH:MM format
    procedure_name: str
    department_executor: str | None = None
    department_executor_cnes: str | None = None
    department_solicitor: str | None = None
    department_solicitor_cnes: str | None = None
    doctor_name: str | None = None
    doctor_cpf: str | None = None
    status: str
    error_message: str | None = None
    error_category: str | None = None
    integration_data: dict | None = None
    source_data: dict | None = None
    reference_date: date
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AppointmentListResponse(BaseModel):
    """Paginated list of appointments."""

    items: list[AppointmentResponse]
    total: int


class AppointmentStatusCounts(BaseModel):
    """Aggregated counts of appointments by status."""

    pending: int = 0
    integrated: int = 0
    skipped: int = 0
    patient_error: int = 0
    appointment_error: int = 0
    mapping_error: int = 0
    data_error: int = 0
    cancelled: int = 0
    completed: int = 0
    no_show: int = 0
