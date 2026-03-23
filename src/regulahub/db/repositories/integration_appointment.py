"""Repository for integration_appointments table."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.models import IntegrationAppointment


class IntegrationAppointmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> IntegrationAppointment:
        """Create a new appointment record."""
        appointment = IntegrationAppointment(**data)
        self._session.add(appointment)
        await self._session.flush()
        return appointment

    async def get_by_id(self, appointment_id: uuid.UUID) -> IntegrationAppointment | None:
        """Get appointment by ID."""
        stmt = select(IntegrationAppointment).where(IntegrationAppointment.id == appointment_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_regulation_code(self, code: str) -> IntegrationAppointment | None:
        """Get appointment by regulation code. Returns the most recent match."""
        stmt = (
            select(IntegrationAppointment)
            .where(IntegrationAppointment.regulation_code == code)
            .where(IntegrationAppointment.is_active.is_(True))
            .order_by(IntegrationAppointment.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str) -> IntegrationAppointment | None:
        """Get appointment by external ID (unique across active records)."""
        stmt = (
            select(IntegrationAppointment)
            .where(IntegrationAppointment.external_id == external_id)
            .where(IntegrationAppointment.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        appointment_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
        error_category: str | None = None,
        integration_data: dict | None = None,
    ) -> IntegrationAppointment | None:
        """Update appointment status, error info, and integration data."""
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None

        appointment.status = status
        appointment.updated_at = datetime.now(UTC)

        if error_message is not None:
            appointment.error_message = error_message
        if error_category is not None:
            appointment.error_category = error_category
        if integration_data is not None:
            appointment.integration_data = integration_data

        await self._session.flush()
        return appointment

    async def list_by_execution(
        self,
        execution_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[IntegrationAppointment], int]:
        """List appointments for an execution with pagination. Returns (items, total)."""
        base = (
            select(IntegrationAppointment)
            .where(IntegrationAppointment.execution_id == execution_id)
            .where(IntegrationAppointment.is_active.is_(True))
        )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        items_stmt = base.order_by(IntegrationAppointment.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(items_stmt)
        items = list(result.scalars().all())

        return items, total

    async def list_filtered(
        self,
        system_id: uuid.UUID | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[IntegrationAppointment], int]:
        """List appointments with optional filters and pagination. Returns (items, total)."""
        base = select(IntegrationAppointment).where(IntegrationAppointment.is_active.is_(True))

        if system_id is not None:
            base = base.where(IntegrationAppointment.integration_system_id == system_id)
        if status is not None:
            base = base.where(IntegrationAppointment.status == status)
        if date_from is not None:
            base = base.where(IntegrationAppointment.appointment_date >= date_from)
        if date_to is not None:
            base = base.where(IntegrationAppointment.appointment_date <= date_to)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        items_stmt = base.order_by(IntegrationAppointment.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(items_stmt)
        items = list(result.scalars().all())

        return items, total

    async def bulk_create(self, items: list[dict]) -> int:
        """Batch insert appointment records. Returns count of inserted rows."""
        if not items:
            return 0

        objects = [IntegrationAppointment(**item) for item in items]
        self._session.add_all(objects)
        await self._session.flush()
        return len(objects)

    async def count_by_status(self, execution_id: uuid.UUID | None = None) -> dict[str, int]:
        """Count appointments grouped by status. Optionally filter by execution_id. Returns {status: count}."""
        base = select(
            IntegrationAppointment.status,
            func.count(IntegrationAppointment.id),
        ).where(IntegrationAppointment.is_active.is_(True))

        if execution_id is not None:
            base = base.where(IntegrationAppointment.execution_id == execution_id)

        stmt = base.group_by(IntegrationAppointment.status)
        result = await self._session.execute(stmt)

        return dict(result.all())
