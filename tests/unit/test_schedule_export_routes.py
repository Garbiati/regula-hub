"""Tests for schedule export admin routes."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from regulahub.api.controllers.admin.schedule_export_routes import router
from regulahub.api.rate_limit import limiter
from regulahub.config import get_auth_settings
from regulahub.services.credential_service import CredentialNotFoundError
from regulahub.sisreg.models import ScheduleExportResponse, ScheduleExportRow

VALID_KEY = "test-api-key-for-export"

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


def _body(**overrides):
    base = {
        "date_from": "19/03/2026",
        "date_to": "31/03/2026",
        "profile_type": "SOLICITANTE",
        "usernames": ["op1"],
    }
    base.update(overrides)
    return base


def _mock_response(rows=None, operators_queried=1, operators_succeeded=1):
    if rows is None:
        rows = [
            ScheduleExportRow(
                solicitacao="100",
                descricao_procedimento="TELECONSULTA",
                nome="JOAO",
                cns="111222333444555",
                situacao="PENDENTE",
            )
        ]
    return ScheduleExportResponse(
        items=rows,
        total=len(rows),
        operators_queried=operators_queried,
        operators_succeeded=operators_succeeded,
    )


class TestScheduleExportJson:
    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.export_schedules")
    async def test_json_success(self, mock_export, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_export.return_value = _mock_response()

        resp = await client.post(
            "/api/admin/sisreg/schedule-export",
            json=_body(),
            headers=_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["solicitacao"] == "100"
        assert data["operators_queried"] == 1

    @pytest.mark.asyncio
    async def test_missing_auth_returns_403(self, client):
        resp = await client.post(
            "/api/admin/sisreg/schedule-export",
            json=_body(),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_date_returns_422(self, client):
        resp = await client.post(
            "/api/admin/sisreg/schedule-export",
            json=_body(date_from="2026-03-19"),
            headers=_headers(),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.export_schedules")
    async def test_no_credentials_returns_503(self, mock_export, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_export.side_effect = CredentialNotFoundError("No credentials")

        resp = await client.post(
            "/api/admin/sisreg/schedule-export",
            json=_body(),
            headers=_headers(),
        )
        assert resp.status_code == 503


class TestSingleOperatorExport:
    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.export_single_operator_resolved")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.resolve_credential_by_username")
    async def test_single_operator_success(self, mock_resolve, mock_export, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_resolve.return_value = ("op1", "pass")
        mock_export.return_value = [
            ScheduleExportRow(
                solicitacao="200",
                descricao_procedimento="CONSULTA",
                nome="MARIA",
                cns="999888777666555",
                situacao="AGENDADO",
            )
        ]

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/operator",
            json=_body(usernames=["op1"]),
            headers=_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["operator"] == "op1"
        assert data["total"] == 1
        assert data["items"][0]["solicitacao"] == "200"

    @pytest.mark.asyncio
    async def test_single_operator_rejects_multiple_usernames(self, client):
        resp = await client.post(
            "/api/admin/sisreg/schedule-export/operator",
            json=_body(usernames=["op1", "op2"]),
            headers=_headers(),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.resolve_credential_by_username")
    async def test_single_operator_credential_not_found(self, mock_resolve, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_resolve.side_effect = CredentialNotFoundError("Not found")

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/operator",
            json=_body(usernames=["op1"]),
            headers=_headers(),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.export_single_operator_resolved")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.resolve_credential_by_username")
    async def test_single_operator_applies_procedure_filter(self, mock_resolve, mock_export, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_resolve.return_value = ("op1", "pass")
        mock_export.return_value = [
            ScheduleExportRow(solicitacao="300", descricao_procedimento="TELECONSULTA EM CARDIOLOGIA"),
            ScheduleExportRow(solicitacao="301", descricao_procedimento="RAIO X TORAX"),
        ]

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/operator",
            json=_body(usernames=["op1"], procedure_filter="teleconsulta"),
            headers=_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["solicitacao"] == "300"


class TestScheduleExportCsv:
    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.export_schedules")
    async def test_csv_download(self, mock_export, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_export.return_value = _mock_response()

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/csv",
            json=_body(),
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        assert "schedule_export_" in resp.headers["content-disposition"]
        # CSV content check
        content = resp.text
        assert "solicitacao;" in content
        assert "100;" in content


class TestScheduleExportTxt:
    @pytest.mark.asyncio
    @patch("regulahub.api.controllers.admin.schedule_export_routes.get_session")
    @patch("regulahub.api.controllers.admin.schedule_export_routes.export_schedules")
    async def test_txt_download(self, mock_export, mock_session, client):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_export.return_value = _mock_response()

        resp = await client.post(
            "/api/admin/sisreg/schedule-export/txt",
            json=_body(),
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        content = resp.text
        assert "\t" in content
