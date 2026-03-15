"""Integration tests for the Absens-compatible endpoints — full request flow with mocked SisReg."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from regulahub.api.controllers.compat.absens_routes import router
from regulahub.api.controllers.compat.absens_schemas import AbsensAppointmentResponse, AbsensDetailResponse
from regulahub.api.rate_limit import limiter
from regulahub.config import get_auth_settings

VALID_KEY = "integration-test-key"

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


class TestIntegrationListFlow:
    async def test_full_list_flow(self, client):
        """T23: Full listing flow — request → service → JSON with exact camelCase fields."""
        mock_results = [
            AbsensAppointmentResponse(
                cod="AAA-001",
                department_execute="HOSPITAL REGIONAL",
                department_solicitation="UBS CENTRO",
                procedure="TELECONSULTA EM CARDIOLOGIA",
                status_sisreg="AGE/PEN/EXEC",
            ),
            AbsensAppointmentResponse(
                cod="AAA-002",
                department_execute="HOSPITAL NORTE",
                department_solicitation="UBS SUL",
                procedure="TELECONSULTA EM DERMATOLOGIA",
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
        assert len(data) == 2

        # Verify exact keys on first item
        expected_keys = {
            "cod",
            "patientBirthday",
            "patientMotherName",
            "departmentExecute",
            "departmentSolicitation",
            "procedure",
            "statusSisreg",
        }
        assert set(data[0].keys()) == expected_keys

        # Verify required strings are never null
        required_str_keys = [
            "cod",
            "patientBirthday",
            "patientMotherName",
            "departmentExecute",
            "departmentSolicitation",
            "procedure",
        ]
        for item in data:
            for key in required_str_keys:
                assert item[key] is not None, f"{key} must not be null"
                assert isinstance(item[key], str), f"{key} must be string"


class TestIntegrationDetailFlow:
    async def test_full_detail_flow(self, client):
        """T24: Full detail flow — request → service → JSON with exact camelCase fields and ● format."""
        from regulahub.api.controllers.compat.absens_schemas import PatientPhoneResponse

        mock_result = AbsensDetailResponse(
            cod="12345",
            confirmation_key="CONF-ABC-123",
            cns="898001234567890",
            patient_phones=[PatientPhoneResponse(ddd="92", number="98765-4321")],
            appointment_date="SEX ● 20/03/2026 ● 14h30min",
            best_phone=PatientPhoneResponse(ddd="92", number="98765-4321"),
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

        # Verify key fields
        assert data["cod"] == "12345"
        assert data["confirmationKey"] == "CONF-ABC-123"
        assert data["cns"] == "898001234567890"
        assert "●" in data["appointmentDate"]
        assert data["bestPhone"]["ddd"] == "92"

        # Verify all 16 expected keys present
        expected_keys = {
            "id",
            "cod",
            "confirmationKey",
            "patient",
            "patientCPF",
            "cns",
            "patientPhones",
            "departmentSolicitation",
            "departmentExecute",
            "appointmentDateTimestamp",
            "appointmentDate",
            "statusSisreg",
            "doctorExecute",
            "status",
            "bestPhone",
            "departmentSolicitationInfos",
        }
        assert set(data.keys()) == expected_keys


class TestJsonDeserialization:
    async def test_json_is_deserializable(self, client):
        """T25: Verify JSON output is valid and types match .NET expectations."""
        mock_result = AbsensDetailResponse(
            cod="99999",
            confirmation_key="CK-1",
            cns="123456789012345",
            appointment_date="QUA ● 18/03/2026 ● 10h00min",
        )

        with patch("regulahub.api.controllers.compat.absens_routes.fetch_detail", new_callable=AsyncMock) as mock:
            mock.return_value = mock_result
            resp = await client.get(
                "/api/compat/absens/agendamentos",
                params={"codigo": "99999"},
                headers=_auth_headers(),
            )

        raw = resp.content.decode()
        data = json.loads(raw)

        # Required strings must be str (not null)
        required_strings = [
            "cod",
            "confirmationKey",
            "patient",
            "cns",
            "departmentSolicitation",
            "departmentExecute",
            "appointmentDate",
            "statusSisreg",
            "doctorExecute",
            "status",
        ]
        for key in required_strings:
            assert isinstance(data[key], str), f"{key} must be string, got {type(data[key])}"

        # Nullable fields can be null
        nullable_fields = [
            "id",
            "patientCPF",
            "patientPhones",
            "appointmentDateTimestamp",
            "bestPhone",
            "departmentSolicitationInfos",
        ]
        for key in nullable_fields:
            assert data[key] is None or isinstance(data[key], str | list | dict), f"{key} has unexpected type"
