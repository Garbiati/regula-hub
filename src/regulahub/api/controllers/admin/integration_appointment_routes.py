"""Admin routes for integration appointment management."""

import csv
import io
import json
import logging
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.api.controllers.admin.integration_appointment_schemas import (
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentStatusCounts,
    AppointmentUpdateRequest,
    DischargeWebhookRequest,
)
from regulahub.api.deps import verify_api_key
from regulahub.api.rate_limit import limiter
from regulahub.db.engine import get_session
from regulahub.db.repositories.integration_appointment import IntegrationAppointmentRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/integrations/appointments",
    tags=["admin-integration-appointments"],
    dependencies=[Depends(verify_api_key)],
)

webhook_router = APIRouter(
    prefix="/api/webhooks",
    tags=["webhooks"],
    dependencies=[Depends(verify_api_key)],
)


def _appointment_to_response(appointment) -> AppointmentResponse:  # noqa: ANN001
    """Convert a DB IntegrationAppointment model to an API response."""
    return AppointmentResponse(
        id=appointment.id,
        integration_system_id=appointment.integration_system_id,
        execution_id=appointment.execution_id,
        regulation_code=appointment.regulation_code,
        confirmation_key=appointment.confirmation_key,
        external_id=appointment.external_id,
        patient_name=appointment.patient_name,
        patient_cpf=appointment.patient_cpf,
        patient_cns=appointment.patient_cns,
        patient_birth_date=appointment.patient_birth_date,
        patient_phone=appointment.patient_phone,
        patient_mother_name=appointment.patient_mother_name,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time.strftime("%H:%M") if appointment.appointment_time else None,
        procedure_name=appointment.procedure_name,
        department_executor=appointment.department_executor,
        department_executor_cnes=appointment.department_executor_cnes,
        department_solicitor=appointment.department_solicitor,
        department_solicitor_cnes=appointment.department_solicitor_cnes,
        doctor_name=appointment.doctor_name,
        doctor_cpf=appointment.doctor_cpf,
        status=appointment.status,
        error_message=appointment.error_message,
        error_category=appointment.error_category,
        integration_data=appointment.integration_data,
        source_data=appointment.source_data,
        reference_date=appointment.reference_date,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
    )


APPOINTMENT_EXPORT_COLUMNS: list[str] = [
    "id",
    "integration_system_id",
    "execution_id",
    "regulation_code",
    "confirmation_key",
    "external_id",
    "patient_name",
    "patient_cpf",
    "patient_cns",
    "patient_birth_date",
    "patient_phone",
    "patient_mother_name",
    "appointment_date",
    "appointment_time",
    "procedure_name",
    "department_executor",
    "department_executor_cnes",
    "department_solicitor",
    "department_solicitor_cnes",
    "doctor_name",
    "doctor_cpf",
    "status",
    "error_message",
    "error_category",
    "integration_data",
    "source_data",
    "reference_date",
    "created_at",
    "updated_at",
]


def build_appointment_csv_bytes(appointments: list) -> bytes:  # noqa: ANN001
    """Build CSV bytes from IntegrationAppointment model instances."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")

    writer.writerow(APPOINTMENT_EXPORT_COLUMNS)

    for appt in appointments:
        row = []
        for col in APPOINTMENT_EXPORT_COLUMNS:
            value = getattr(appt, col)
            if col == "appointment_time" and value is not None:
                value = value.strftime("%H:%M")
            elif col in ("integration_data", "source_data") and value is not None:
                value = json.dumps(value, ensure_ascii=False, default=str)
            elif value is None:
                value = ""
            row.append(value)
        writer.writerow(row)

    return output.getvalue().encode("utf-8")


@router.get("/", response_model=AppointmentListResponse)
@limiter.limit("30/minute")
async def list_appointments(
    request: Request,
    status: str | None = Query(None, description="Filter by appointment status"),
    date_from: date | None = Query(None, description="Filter appointments from this date"),
    date_to: date | None = Query(None, description="Filter appointments up to this date"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_session),
) -> AppointmentListResponse:
    """List appointments with optional filters and pagination."""
    repo = IntegrationAppointmentRepository(db)
    items, total = await repo.list_filtered(
        status=status,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )

    return AppointmentListResponse(
        items=[_appointment_to_response(appt) for appt in items],
        total=total,
    )


@router.get("/counts", response_model=AppointmentStatusCounts)
@limiter.limit("30/minute")
async def get_appointment_counts(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> AppointmentStatusCounts:
    """Get aggregated appointment counts by status."""
    repo = IntegrationAppointmentRepository(db)
    counts = await repo.count_by_status()

    return AppointmentStatusCounts(
        pending=counts.get("pending", 0),
        integrated=counts.get("integrated", 0),
        skipped=counts.get("skipped", 0),
        patient_error=counts.get("patient_error", 0),
        appointment_error=counts.get("appointment_error", 0),
        mapping_error=counts.get("mapping_error", 0),
        data_error=counts.get("data_error", 0),
        cancelled=counts.get("cancelled", 0),
        completed=counts.get("completed", 0),
        no_show=counts.get("no_show", 0),
    )


@router.get("/export/csv")
@limiter.limit("3/minute")
async def export_appointments_csv(
    request: Request,
    status: str | None = Query(None, description="Filter by appointment status"),
    date_from: date | None = Query(None, description="Filter appointments from this date"),
    date_to: date | None = Query(None, description="Filter appointments up to this date"),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Export all matching appointments as CSV file download."""
    repo = IntegrationAppointmentRepository(db)
    appointments = await repo.list_all_filtered(
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    csv_bytes = build_appointment_csv_bytes(appointments)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")

    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="integration_appointments_{timestamp}.csv"'},
    )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
@limiter.limit("30/minute")
async def get_appointment(
    request: Request,
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> AppointmentResponse:
    """Get a single appointment by ID."""
    repo = IntegrationAppointmentRepository(db)
    appointment = await repo.get_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return _appointment_to_response(appointment)


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
@limiter.limit("10/minute")
async def update_appointment(
    request: Request,
    appointment_id: uuid.UUID,
    body: AppointmentUpdateRequest,
    db: AsyncSession = Depends(get_session),
) -> AppointmentResponse:
    """Update appointment data for error correction before retry. Only provided (non-None) fields are updated."""
    repo = IntegrationAppointmentRepository(db)
    appointment = await repo.get_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields provided for update")

    for field, value in update_data.items():
        setattr(appointment, field, value)
    appointment.updated_at = datetime.now(UTC)

    await db.flush()

    return _appointment_to_response(appointment)


@router.post("/{appointment_id}/retry", response_model=AppointmentResponse)
@limiter.limit("10/minute")
async def retry_appointment(
    request: Request,
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> AppointmentResponse:
    """Retry push for a failed appointment. Resets status to pending for the next execution cycle."""
    repo = IntegrationAppointmentRepository(db)
    appointment = await repo.get_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    retryable_statuses = {"patient_error", "appointment_error", "mapping_error", "data_error"}
    if appointment.status not in retryable_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot retry appointment with status '{appointment.status}'. "
            f"Only appointments with error status can be retried.",
        )

    appointment.status = "awaiting_integration"
    appointment.error_message = None
    appointment.error_category = None
    appointment.updated_at = datetime.now(UTC)
    await db.flush()

    return _appointment_to_response(appointment)


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
@limiter.limit("10/minute")
async def cancel_appointment(
    request: Request,
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> AppointmentResponse:
    """Cancel an appointment. Sets status to cancelled."""
    repo = IntegrationAppointmentRepository(db)
    appointment = await repo.get_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    non_cancellable = {"cancelled", "completed", "no_show"}
    if appointment.status in non_cancellable:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot cancel appointment with status '{appointment.status}'.",
        )

    appointment.status = "cancelled"
    appointment.updated_at = datetime.now(UTC)
    await db.flush()

    return _appointment_to_response(appointment)


# ── Webhook endpoints ────────────────────────────────────────────────────


@webhook_router.post("/discharge", status_code=200)
@limiter.limit("10/minute")
async def discharge_webhook(
    request: Request,
    body: DischargeWebhookRequest,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Webhook for external systems to report appointment discharge (completed/no_show)."""
    repo = IntegrationAppointmentRepository(db)
    appointment = await repo.get_by_external_id(body.external_id)
    if not appointment:
        raise HTTPException(status_code=404, detail=f"Appointment with external_id '{body.external_id}' not found")

    terminal_statuses = {"cancelled", "completed", "no_show"}
    if appointment.status in terminal_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Appointment already in terminal status '{appointment.status}'.",
        )

    appointment.status = body.status
    appointment.updated_at = datetime.now(UTC)

    # Store discharge metadata in integration_data
    discharge_info = {"discharged_at": body.discharged_at.isoformat() if body.discharged_at else None}
    if body.doctor_id:
        discharge_info["doctor_id"] = body.doctor_id
    if body.notes:
        discharge_info["notes"] = body.notes

    existing_data = appointment.integration_data or {}
    existing_data["discharge"] = discharge_info
    appointment.integration_data = existing_data

    await db.flush()

    logger.info(
        "Discharge webhook processed: external_id=%s, status=%s",
        body.external_id,
        body.status,
    )

    return {"external_id": body.external_id, "status": body.status, "appointment_id": str(appointment.id)}
