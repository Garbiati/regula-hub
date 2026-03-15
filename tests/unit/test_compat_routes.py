"""Tests for Absens-compatible API routes."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from regulahub.api.controllers.compat.absens_routes import router
from regulahub.api.controllers.compat.absens_schemas import AbsensAppointmentResponse, AbsensDetailResponse
from regulahub.api.rate_limit import limiter
from regulahub.config import get_auth_settings
from regulahub.services.credential_service import CredentialNotFoundError
from regulahub.sisreg.client import SisregLoginError

VALID_KEY = "test-api-key-for-compat"

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


def _auth_headers():
    return {"Authorization": VALID_KEY}


class TestAgendamentosValidation:
    async def test_no_params_returns_422(self, client):
        """T16: Missing both date and codigo → 422."""
        resp = await client.get("/api/compat/absens/agendamentos", headers=_auth_headers())
        assert resp.status_code == 422

    async def test_both_params_returns_422(self, client):
        """T17: Both date and codigo → 422."""
        resp = await client.get(
            "/api/compat/absens/agendamentos",
            params={"date": "2026-03-18", "codigo": "123"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    async def test_invalid_date_returns_422(self, client):
        """T18: Invalid date format → 422."""
        resp = await client.get(
            "/api/compat/absens/agendamentos",
            params={"date": "invalid"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422


class TestCancelamentos:
    async def test_returns_empty_list(self, client):
        """T19: Cancelamentos always returns empty list."""
        resp = await client.get(
            "/api/compat/absens/cancelamentos",
            params={"date": "2026-03-18"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestAuth:
    async def test_missing_auth_returns_401(self, client):
        """T20: No Authorization header → 401."""
        resp = await client.get("/api/compat/absens/agendamentos", params={"date": "2026-03-18"})
        assert resp.status_code == 401


class TestAgendamentosValidationCalendarDate:
    async def test_invalid_calendar_date_returns_422(self, client):
        """T26: Valid format but invalid calendar date (Feb 30) → 422."""
        resp = await client.get(
            "/api/compat/absens/agendamentos",
            params={"date": "2026-02-30"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422
        assert "Invalid calendar date" in resp.json()["detail"]

    async def test_impossible_month_returns_422(self, client):
        """T27: Month 13 → 422."""
        resp = await client.get(
            "/api/compat/absens/agendamentos",
            params={"date": "2026-13-01"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422


class TestAgendamentosErrorPaths:
    async def test_credential_not_found_date_returns_503(self, client):
        """T28: CredentialNotFoundError on date path → 503."""
        with patch(
            "regulahub.api.controllers.compat.absens_routes.fetch_appointments",
            new_callable=AsyncMock,
            side_effect=CredentialNotFoundError("No VIDEOFONISTA credentials configured for SISREG"),
        ):
            resp = await client.get(
                "/api/compat/absens/agendamentos",
                params={"date": "2026-03-18"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 503

    async def test_credential_not_found_codigo_returns_503(self, client):
        """T29: CredentialNotFoundError on codigo path → 503."""
        with patch(
            "regulahub.api.controllers.compat.absens_routes.fetch_detail",
            new_callable=AsyncMock,
            side_effect=CredentialNotFoundError("No credentials"),
        ):
            resp = await client.get(
                "/api/compat/absens/agendamentos",
                params={"codigo": "12345"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 503

    async def test_sisreg_login_error_codigo_returns_502(self, client):
        """T30: SisregLoginError on codigo path → 502."""
        with patch(
            "regulahub.api.controllers.compat.absens_routes.fetch_detail",
            new_callable=AsyncMock,
            side_effect=SisregLoginError("Login failed"),
        ):
            resp = await client.get(
                "/api/compat/absens/agendamentos",
                params={"codigo": "12345"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 502
        assert "SisReg login failed" in resp.json()["detail"]

    async def test_generic_exception_date_returns_502(self, client):
        """T31: Generic exception on date path → 502."""
        with patch(
            "regulahub.api.controllers.compat.absens_routes.fetch_appointments",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected error"),
        ):
            resp = await client.get(
                "/api/compat/absens/agendamentos",
                params={"date": "2026-03-18"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 502
        assert "SisReg search failed" in resp.json()["detail"]

    async def test_generic_exception_codigo_returns_502(self, client):
        """T32: Generic exception on codigo path → 502."""
        with patch(
            "regulahub.api.controllers.compat.absens_routes.fetch_detail",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected error"),
        ):
            resp = await client.get(
                "/api/compat/absens/agendamentos",
                params={"codigo": "12345"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 502
        assert "SisReg detail fetch failed" in resp.json()["detail"]


class TestCancelamentosWithoutParams:
    async def test_no_params_returns_empty_list(self, client):
        """T33: Cancelamentos without params → empty list."""
        resp = await client.get("/api/compat/absens/cancelamentos", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == []


class TestAgendamentosListByDate:
    async def test_returns_json_array_camel_case(self, client):
        """T21: List by date returns camelCase JSON array."""
        mock_results = [
            AbsensAppointmentResponse(
                cod="12345",
                department_execute="HOSPITAL",
                department_solicitation="UBS",
                procedure="TELECONSULTA",
                status_sisreg="AGE",
            ),
        ]

        with patch("regulahub.api.controllers.compat.absens_routes.fetch_appointments", new_callable=AsyncMock) as mock:
            mock.return_value = mock_results
            resp = await client.get(
                "/api/compat/absens/agendamentos",
                params={"date": "2026-03-18"},
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["cod"] == "12345"
        assert "departmentExecute" in data[0]
        assert "patientBirthday" in data[0]


class TestAgendamentosDetailByCode:
    async def test_returns_json_object_camel_case(self, client):
        """T22: Detail by code returns camelCase JSON object."""
        mock_result = AbsensDetailResponse(
            cod="12345",
            confirmation_key="CONF-123",
            cns="898001234567890",
            appointment_date="QUA ● 20/03/2026 ● 14h00min",
        )

        with patch("regulahub.api.controllers.compat.absens_routes.fetch_detail", new_callable=AsyncMock) as mock:
            mock.return_value = mock_result
            resp = await client.get(
                "/api/compat/absens/agendamentos",
                params={"codigo": "12345"},
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert data["cod"] == "12345"
        assert data["confirmationKey"] == "CONF-123"
        assert data["appointmentDate"] == "QUA ● 20/03/2026 ● 14h00min"
