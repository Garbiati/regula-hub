"""Tests for /enrich endpoint with enrichment cache."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from regulahub.api.controllers.admin.schedule_export_routes import router
from regulahub.api.rate_limit import limiter
from regulahub.config import get_auth_settings
from regulahub.db.models import Base, CachedEnrichment

VALID_KEY = "test-api-key-for-enrich-cache"

app = FastAPI()
app.include_router(router)


@pytest.fixture(autouse=True)
def _set_api_keys(monkeypatch):
    monkeypatch.setenv("API_KEYS", VALID_KEY)
    get_auth_settings.cache_clear()
    limiter.enabled = False
    yield
    limiter.enabled = True
    get_auth_settings.cache_clear()


def _headers():
    return {"X-API-Key": VALID_KEY}


def _body(cns_list=None, **overrides):
    base = {
        "cns_list": cns_list or ["CNS001", "CNS002"],
        "phone_fallbacks": {},
    }
    base.update(overrides)
    return base


class TestEnrichWithCache:
    @pytest.fixture
    async def db_session(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            yield session

        await engine.dispose()

    @pytest.fixture
    async def client(self, db_session):
        async def _override_session():
            yield db_session

        app.dependency_overrides.clear()
        from regulahub.db.engine import get_session

        app.dependency_overrides[get_session] = _override_session

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    @patch("regulahub.config.get_cadsus_settings")
    async def test_returns_cached_without_calling_cadsus(self, mock_settings, client, db_session):
        """Fresh cache entries should be returned without calling CADSUS."""
        mock_settings.return_value = MagicMock(cadsus_enabled=False)

        # Seed cache with fresh entries
        db_session.add(CachedEnrichment(
            cns="CNS001", cpf="11111111111", phone="(92)99999-0001",
            source="CADSUS", enriched_at=datetime.now(UTC),
        ))
        db_session.add(CachedEnrichment(
            cns="CNS002", cpf="22222222222", phone="(92)99999-0002",
            source="CADSUS", enriched_at=datetime.now(UTC),
        ))
        await db_session.flush()

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/enrich",
            json=_body(cns_list=["CNS001", "CNS002"]),
            headers=_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["from_cache"] == 2
        assert data["found"] == 2
        assert data["failed"] == 0
        assert "CNS001" in data["results"]
        assert data["results"]["CNS001"]["cpf"] == "11111111111"

    @pytest.mark.asyncio
    @patch("regulahub.config.get_cadsus_settings")
    async def test_stale_cache_is_ignored(self, mock_settings, client, db_session):
        """Entries older than 30 days should not be used from cache."""
        mock_settings.return_value = MagicMock(cadsus_enabled=False)

        stale_date = datetime.now(UTC) - timedelta(days=31)
        db_session.add(CachedEnrichment(
            cns="CNS001", cpf="11111111111", phone="(92)99999-0001",
            source="CADSUS", enriched_at=stale_date,
        ))
        await db_session.flush()

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/enrich",
            json=_body(cns_list=["CNS001"]),
            headers=_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["from_cache"] == 0
        assert data["failed"] == 1  # CADSUS disabled, so it fails

    @pytest.mark.asyncio
    @patch("regulahub.config.get_cadsus_settings")
    async def test_mixed_cached_and_pending(self, mock_settings, client, db_session):
        """Cached CNS should be returned; non-cached should go through CADSUS pipeline."""
        mock_settings.return_value = MagicMock(cadsus_enabled=False)

        # Only CNS001 is cached
        db_session.add(CachedEnrichment(
            cns="CNS001", cpf="11111111111", phone="(92)99999-0001",
            source="CADSUS", enriched_at=datetime.now(UTC),
        ))
        await db_session.flush()

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/enrich",
            json=_body(cns_list=["CNS001", "CNS002"]),
            headers=_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["from_cache"] == 1
        assert data["found"] == 1  # Only CNS001 from cache
        assert data["failed"] == 1  # CNS002 not found (CADSUS disabled)

    @pytest.mark.asyncio
    async def test_missing_auth_returns_403(self, client):
        resp = await client.post(
            "/api/admin/sisreg/schedule-export/enrich",
            json=_body(),
        )
        assert resp.status_code == 403
