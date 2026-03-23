"""Repository for integration mapping tables (departments, procedures, execution mappings)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.models import IntegrationDepartment, IntegrationExecutionMapping, IntegrationProcedure


class IntegrationMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- Departments -------------------------------------------------------

    async def get_department_by_cnes(self, cnes_code: str) -> IntegrationDepartment | None:
        """Fetch a department by its CNES code (exact match)."""
        stmt = (
            select(IntegrationDepartment)
            .where(IntegrationDepartment.cnes_code == cnes_code)
            .where(IntegrationDepartment.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_department_by_name(self, name: str) -> IntegrationDepartment | None:
        """Fetch a department by name (case-insensitive)."""
        stmt = (
            select(IntegrationDepartment)
            .where(func.upper(IntegrationDepartment.department_name) == name.upper())
            .where(IntegrationDepartment.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_departments(self) -> list[IntegrationDepartment]:
        """List all active departments ordered by name."""
        stmt = (
            select(IntegrationDepartment)
            .where(IntegrationDepartment.is_active.is_(True))
            .order_by(IntegrationDepartment.department_name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -- Procedures --------------------------------------------------------

    async def get_procedure_by_name(self, name: str) -> IntegrationProcedure | None:
        """Fetch a procedure by name (case-insensitive ILIKE)."""
        stmt = (
            select(IntegrationProcedure)
            .where(IntegrationProcedure.procedure_name.ilike(name))
            .where(IntegrationProcedure.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_procedures(self) -> list[IntegrationProcedure]:
        """List all active procedures ordered by name."""
        stmt = (
            select(IntegrationProcedure)
            .where(IntegrationProcedure.is_active.is_(True))
            .order_by(IntegrationProcedure.procedure_name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -- Execution Mappings ------------------------------------------------

    async def get_execution_mapping_by_requester_cnes(self, requester_cnes: str) -> IntegrationExecutionMapping | None:
        """Fetch an execution mapping by requester CNES code."""
        stmt = (
            select(IntegrationExecutionMapping)
            .where(IntegrationExecutionMapping.requester_cnes == requester_cnes)
            .where(IntegrationExecutionMapping.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
