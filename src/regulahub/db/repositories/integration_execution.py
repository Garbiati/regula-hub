"""Repository for integration_executions table."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.models import IntegrationExecution


class IntegrationExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> IntegrationExecution:
        """Create a new execution record."""
        execution = IntegrationExecution(**data)
        self._session.add(execution)
        await self._session.flush()
        return execution

    async def get_by_id(self, execution_id: uuid.UUID) -> IntegrationExecution | None:
        """Get execution by ID."""
        stmt = select(IntegrationExecution).where(IntegrationExecution.id == execution_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        execution_id: uuid.UUID,
        status: str,
        *,
        error_message: str | None = None,
        total_fetched: int | None = None,
        total_enriched: int | None = None,
        total_pushed: int | None = None,
        total_failed: int | None = None,
        progress_data: dict | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> IntegrationExecution | None:
        """Update execution status and counters."""
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None

        execution.status = status
        execution.updated_at = datetime.now(UTC)

        if error_message is not None:
            execution.error_message = error_message
        if total_fetched is not None:
            execution.total_fetched = total_fetched
        if total_enriched is not None:
            execution.total_enriched = total_enriched
        if total_pushed is not None:
            execution.total_pushed = total_pushed
        if total_failed is not None:
            execution.total_failed = total_failed
        if progress_data is not None:
            execution.progress_data = progress_data
        if started_at is not None:
            execution.started_at = started_at
        if completed_at is not None:
            execution.completed_at = completed_at

        await self._session.flush()
        return execution

    async def update_progress(self, execution_id: uuid.UUID, progress_data: dict) -> None:
        """Update only progress_data for real-time status polling."""
        execution = await self.get_by_id(execution_id)
        if execution:
            execution.progress_data = progress_data
            execution.updated_at = datetime.now(UTC)
            await self._session.flush()

    async def list_by_system(
        self,
        system_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[IntegrationExecution], int]:
        """List executions for a system with pagination. Returns (items, total)."""
        base = (
            select(IntegrationExecution)
            .where(IntegrationExecution.integration_system_id == system_id)
            .where(IntegrationExecution.is_active.is_(True))
        )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        items_stmt = base.order_by(IntegrationExecution.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(items_stmt)
        items = list(result.scalars().all())

        return items, total

    async def list_all(self, skip: int = 0, limit: int = 20) -> tuple[list[IntegrationExecution], int]:
        """List all executions with pagination. Returns (items, total)."""
        base = select(IntegrationExecution).where(IntegrationExecution.is_active.is_(True))

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        items_stmt = base.order_by(IntegrationExecution.created_at.desc()).offset(skip).limit(limit)
        result = await self._session.execute(items_stmt)
        items = list(result.scalars().all())

        return items, total

    async def get_latest_by_system(self, system_id: uuid.UUID) -> IntegrationExecution | None:
        """Get the most recent execution for a system."""
        stmt = (
            select(IntegrationExecution)
            .where(IntegrationExecution.integration_system_id == system_id)
            .where(IntegrationExecution.is_active.is_(True))
            .order_by(IntegrationExecution.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def has_running_execution(self, system_id: uuid.UUID) -> bool:
        """Check if there is already a running execution for a system."""
        stmt = (
            select(func.count(IntegrationExecution.id))
            .where(IntegrationExecution.integration_system_id == system_id)
            .where(IntegrationExecution.status.in_(["pending", "running"]))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0
