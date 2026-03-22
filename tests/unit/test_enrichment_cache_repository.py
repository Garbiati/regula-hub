"""Tests for EnrichmentCacheRepository using in-memory SQLite."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from regulahub.db.models import Base
from regulahub.db.repositories.enrichment_cache import EnrichmentCacheRepository


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def repo(db_session):
    return EnrichmentCacheRepository(db_session)


def _make_entry(cns: str = "111222333444555", **overrides) -> dict:
    defaults = {
        "cns": cns,
        "cpf": "12345678901",
        "phone": "(92)99138-4577",
        "email": None,
        "father_name": None,
        "race": None,
        "cns_definitivo": None,
        "source": "CADSUS",
        "enriched_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return defaults


async def test_bulk_upsert_creates_entries(repo, db_session):
    entries = [_make_entry("CNS001"), _make_entry("CNS002")]
    count = await repo.bulk_upsert(entries)
    assert count == 2


async def test_bulk_upsert_updates_existing(repo, db_session):
    await repo.bulk_upsert([_make_entry("CNS001", cpf="11111111111")])
    await db_session.flush()

    await repo.bulk_upsert([_make_entry("CNS001", cpf="22222222222")])
    await db_session.flush()

    cached = await repo.find_fresh_by_cns_list(["CNS001"])
    assert len(cached) == 1
    assert cached["CNS001"].cpf == "22222222222"


async def test_find_fresh_returns_recent(repo, db_session):
    await repo.bulk_upsert([_make_entry("CNS001")])
    await db_session.flush()

    cached = await repo.find_fresh_by_cns_list(["CNS001"])
    assert "CNS001" in cached
    assert cached["CNS001"].cpf == "12345678901"


async def test_find_fresh_ignores_stale(repo, db_session):
    stale_date = datetime.now(UTC) - timedelta(days=31)
    await repo.bulk_upsert([_make_entry("CNS001", enriched_at=stale_date)])
    await db_session.flush()

    cached = await repo.find_fresh_by_cns_list(["CNS001"], max_age_days=30)
    assert len(cached) == 0


async def test_find_fresh_respects_custom_ttl(repo, db_session):
    old_date = datetime.now(UTC) - timedelta(days=10)
    await repo.bulk_upsert([_make_entry("CNS001", enriched_at=old_date)])
    await db_session.flush()

    # 30 days TTL — should find it
    cached30 = await repo.find_fresh_by_cns_list(["CNS001"], max_age_days=30)
    assert "CNS001" in cached30

    # 5 days TTL — should NOT find it
    cached5 = await repo.find_fresh_by_cns_list(["CNS001"], max_age_days=5)
    assert len(cached5) == 0


async def test_find_fresh_ignores_inactive(repo, db_session):
    await repo.bulk_upsert([_make_entry("CNS001")])
    await db_session.flush()

    # Deactivate
    from sqlalchemy import select

    from regulahub.db.models import CachedEnrichment

    stmt = select(CachedEnrichment).where(CachedEnrichment.cns == "CNS001")
    result = await db_session.execute(stmt)
    entity = result.scalar_one()
    entity.is_active = False
    await db_session.flush()

    cached = await repo.find_fresh_by_cns_list(["CNS001"])
    assert len(cached) == 0


async def test_find_fresh_filters_by_cns_list(repo, db_session):
    await repo.bulk_upsert([_make_entry("CNS001"), _make_entry("CNS002"), _make_entry("CNS003")])
    await db_session.flush()

    cached = await repo.find_fresh_by_cns_list(["CNS001", "CNS003"])
    assert set(cached.keys()) == {"CNS001", "CNS003"}


async def test_find_fresh_empty_list_returns_empty(repo, db_session):
    cached = await repo.find_fresh_by_cns_list([])
    assert cached == {}


async def test_find_fresh_no_match_returns_empty(repo, db_session):
    await repo.bulk_upsert([_make_entry("CNS001")])
    await db_session.flush()

    cached = await repo.find_fresh_by_cns_list(["CNS999"])
    assert len(cached) == 0
