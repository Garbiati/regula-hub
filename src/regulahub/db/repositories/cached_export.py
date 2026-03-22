"""Repository for sisreg_cached_exports table."""

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.models import CachedScheduleExport

# Fields populated by CADSUS enrichment — preserved on upsert when new value is absent
ENRICHMENT_FIELDS = ("cpf_paciente", "telefone_cadsus", "email_paciente", "nome_pai", "raca", "cns_definitivo")


class CachedExportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_date_range(
        self,
        date_from: date,
        date_to: date,
        procedure_filter: str | None = None,
    ) -> list[CachedScheduleExport]:
        """Query cached rows by ISO date range + optional procedure ILIKE."""
        stmt = (
            select(CachedScheduleExport)
            .where(CachedScheduleExport.is_active.is_(True))
            .where(CachedScheduleExport.data_agendamento_iso >= date_from)
            .where(CachedScheduleExport.data_agendamento_iso <= date_to)
        )
        if procedure_filter:
            stmt = stmt.where(CachedScheduleExport.descricao_procedimento.ilike(f"%{procedure_filter}%"))
        stmt = stmt.order_by(CachedScheduleExport.data_agendamento_iso)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Upsert rows by solicitacao. Returns count upserted.

        Uses merge() for dialect-agnostic behavior (works with both PostgreSQL and SQLite in tests).
        """
        count = 0
        for row_data in rows:
            solicitacao = row_data["solicitacao"]
            stmt = select(CachedScheduleExport).where(CachedScheduleExport.solicitacao == solicitacao)
            result = await self._session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.data_agendamento = row_data["data_agendamento"]
                existing.data_agendamento_iso = row_data.get("data_agendamento_iso")
                existing.descricao_procedimento = row_data["descricao_procedimento"]
                # Smart merge: preserve enrichment fields from previous persist when new data lacks them
                new_row_data = row_data["row_data"]
                old_row_data = existing.row_data or {}
                for field in ENRICHMENT_FIELDS:
                    if not new_row_data.get(field) and old_row_data.get(field):
                        new_row_data[field] = old_row_data[field]
                existing.row_data = new_row_data
                existing.is_active = True
                existing.updated_at = datetime.now(UTC)
            else:
                entity = CachedScheduleExport(**row_data)
                self._session.add(entity)
            count += 1

        await self._session.flush()
        return count

    async def count_by_date_range(
        self,
        date_from: date,
        date_to: date,
        procedure_filter: str | None = None,
    ) -> int:
        """Count matching cached rows."""
        stmt = (
            select(func.count(CachedScheduleExport.id))
            .where(CachedScheduleExport.is_active.is_(True))
            .where(CachedScheduleExport.data_agendamento_iso >= date_from)
            .where(CachedScheduleExport.data_agendamento_iso <= date_to)
        )
        if procedure_filter:
            stmt = stmt.where(CachedScheduleExport.descricao_procedimento.ilike(f"%{procedure_filter}%"))
        result = await self._session.execute(stmt)
        return result.scalar_one()
