"""Tests for cached schedule export admin routes (/cached and /persist)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from regulahub.api.controllers.admin.schedule_export_routes import router
from regulahub.api.rate_limit import limiter
from regulahub.config import get_auth_settings
from regulahub.sisreg.models import ScheduleExportRow

VALID_KEY = "test-api-key-for-cache"

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


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _headers():
    return {"X-API-Key": VALID_KEY}


def _sample_rows():
    return [
        ScheduleExportRow(
            solicitacao="SOL001",
            descricao_procedimento="TELECONSULTA EM DERMATOLOGIA",
            data_agendamento="25/03/2026",
            nome="PACIENTE TESTE",
            cns="111222333444555",
        ),
        ScheduleExportRow(
            solicitacao="SOL002",
            descricao_procedimento="TELECONSULTA EM CARDIOLOGIA",
            data_agendamento="26/03/2026",
            nome="OUTRO PACIENTE",
            cns="222333444555666",
        ),
    ]


class TestQueryCachedExports:
    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_cached_exports")
    async def test_query_cached_success(self, mock_get_cached, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_get_cached.return_value = _sample_rows()

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/cached",
            json={
                "date_from": "01/03/2026",
                "date_to": "31/03/2026",
                "procedure_filter": "TELECONSULTA",
            },
            headers=_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["solicitacao"] == "SOL001"

    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_cached_exports")
    async def test_query_cached_empty(self, mock_get_cached, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_get_cached.return_value = []

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/cached",
            json={
                "date_from": "01/01/2026",
                "date_to": "31/01/2026",
            },
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    @pytest.mark.asyncio
    async def test_query_cached_invalid_date(self, client):
        resp = await client.post(
            "/api/admin/sisreg/schedule-export/cached",
            json={
                "date_from": "2026-03-01",
                "date_to": "31/03/2026",
            },
            headers=_headers(),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_query_cached_missing_auth(self, client):
        resp = await client.post(
            "/api/admin/sisreg/schedule-export/cached",
            json={
                "date_from": "01/03/2026",
                "date_to": "31/03/2026",
            },
        )
        assert resp.status_code == 403


class TestPersistExportRows:
    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.persist_export_rows")
    async def test_persist_success(self, mock_persist, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_persist.return_value = 2

        items = [
            {
                "solicitacao": "SOL001",
                "descricao_procedimento": "TELECONSULTA",
                "data_agendamento": "25/03/2026",
            },
            {
                "solicitacao": "SOL002",
                "descricao_procedimento": "TELECONSULTA",
                "data_agendamento": "26/03/2026",
            },
        ]

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/persist",
            json={"items": items},
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["persisted"] == 2

    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.persist_export_rows")
    async def test_persist_empty_items(self, mock_persist, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_persist.return_value = 0

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/persist",
            json={"items": []},
            headers=_headers(),
        )
        # Empty items should be rejected by max_length validation (min is implicit via required)
        # Actually empty list is fine, it's max_length=10000
        assert resp.status_code == 200
        assert resp.json()["persisted"] == 0

    @pytest.mark.asyncio
    async def test_persist_missing_auth(self, client):
        resp = await client.post(
            "/api/admin/sisreg/schedule-export/persist",
            json={"items": [{"solicitacao": "SOL001"}]},
        )
        assert resp.status_code == 403
