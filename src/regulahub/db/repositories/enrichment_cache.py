"""Repository for cadsus_enrichment_cache table."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.models import CachedEnrichment

ENRICHMENT_CACHE_TTL_DAYS = 30


class EnrichmentCacheRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_fresh_by_cns_list(
        self,
        cns_list: list[str],
        max_age_days: int = ENRICHMENT_CACHE_TTL_DAYS,
    ) -> dict[str, CachedEnrichment]:
        """Return cached enrichments where enriched_at > now - max_age_days.

        Single IN query — no N+1. Returns dict keyed by CNS for O(1) lookup.
        """
        if not cns_list:
            return {}

        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
        stmt = (
            select(CachedEnrichment)
            .where(CachedEnrichment.cns.in_(cns_list))
            .where(CachedEnrichment.enriched_at >= cutoff)
            .where(CachedEnrichment.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        entries = result.scalars().all()
        return {e.cns: e for e in entries}

    async def bulk_upsert(self, entries: list[dict]) -> int:
        """Upsert enrichment entries by CNS. Returns count upserted."""
        count = 0
        for entry_data in entries:
            cns = entry_data["cns"]
            stmt = select(CachedEnrichment).where(CachedEnrichment.cns == cns)
            result = await self._session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                for key, value in entry_data.items():
                    if key not in ("id", "cns", "created_at") and hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.now(UTC)
            else:
                entity = CachedEnrichment(**entry_data)
                self._session.add(entity)
            count += 1

        await self._session.flush()
        return count
