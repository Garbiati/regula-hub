"""Tests for IntegrationPushClient using respx mocks."""

import uuid
from types import SimpleNamespace

import respx
from httpx import Response

from regulahub.services.integration_push_client import IntegrationPushClient

SYSTEM_ID = uuid.uuid4()
BASE_URL = "https://integration-api.example.com"


def _make_system():
    return SimpleNamespace(
        id=SYSTEM_ID,
        code="TEST_SYSTEM",
        name="Test System",
        base_url=BASE_URL,
    )


def _make_endpoint(name: str, method: str, path: str):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        protocol="REST",
        http_method=method,
        path=path,
        base_url_override=None,
        config={"auth_pattern": "api_key"},
        is_active=True,
    )


def _make_endpoints() -> list:
    return [
        _make_endpoint("find_patient", "GET", "/api/patients"),
        _make_endpoint("register_patient", "POST", "/api/patients"),
        _make_endpoint("update_patient", "PUT", "/api/patients/{id}"),
        _make_endpoint("list_doctors", "GET", "/api/doctors"),
        _make_endpoint("find_reminder", "GET", "/api/reminders"),
        _make_endpoint("create_reminder", "POST", "/api/reminders"),
    ]


def _make_enriched_appointment() -> dict:
    return {
        "code": "1234567890",
        "patient_cns": "111222333444555",
        "patient_name": "PACIENTE TESTE",
        "patient_cpf": "123.456.789-00",
        "patient_birth_date": "15/04/1990",
        "patient_mother_name": "MARIA DA SILVA",
        "patient_phone": "98765-4321",
        "patient_phone_ddd": "92",
        "doctor_name": "DR. SILVA",
        "appointment_date": "25/03/2026 14:30",
        "procedure": "TELECONSULTA EM CARDIOLOGIA",
        "department": "HOSPITAL REGIONAL",
        "department_solicitation": "UBS CENTRO",
        "confirmation_key": "ABC123",
        "status": "AGENDADO",
    }


@respx.mock
async def test_find_patient_found():
    patient_data = {"id": "p-001", "cns": "111222333444555", "name": "PACIENTE TESTE"}
    respx.get(f"{BASE_URL}/api/patients").mock(return_value=Response(200, json=[patient_data]))

    async with IntegrationPushClient(_make_system(), _make_endpoints()) as client:
        result = await client.find_patient("111222333444555")
        assert result is not None
        assert result["id"] == "p-001"


@respx.mock
async def test_find_patient_not_found():
    respx.get(f"{BASE_URL}/api/patients").mock(return_value=Response(200, json=[]))

    async with IntegrationPushClient(_make_system(), _make_endpoints()) as client:
        result = await client.find_patient("999999999999999")
        assert result is None


@respx.mock
async def test_register_patient():
    created = {"id": "p-002", "cns": "111222333444555"}
    respx.post(f"{BASE_URL}/api/patients").mock(return_value=Response(201, json=created))

    async with IntegrationPushClient(_make_system(), _make_endpoints()) as client:
        result = await client.register_patient({"cns": "111222333444555", "name": "PACIENTE"})
        assert result is not None
        assert result["id"] == "p-002"


@respx.mock
async def test_list_doctors_cached():
    doctors = [{"id": "d-001", "name": "DR. SILVA"}]
    route = respx.get(f"{BASE_URL}/api/doctors").mock(return_value=Response(200, json=doctors))

    async with IntegrationPushClient(_make_system(), _make_endpoints()) as client:
        result1 = await client.list_doctors()
        result2 = await client.list_doctors()
        assert result1 == result2
        assert route.call_count == 1  # Cached on second call


@respx.mock
async def test_create_reminder():
    reminder = {"id": "r-001", "patientId": "p-001"}
    respx.post(f"{BASE_URL}/api/reminders").mock(return_value=Response(201, json=reminder))

    async with IntegrationPushClient(_make_system(), _make_endpoints()) as client:
        result = await client.create_reminder({"patientId": "p-001", "appointmentDate": "25/03/2026"})
        assert result is not None
        assert result["id"] == "r-001"


@respx.mock
async def test_process_appointment_full_flow_new_patient():
    """Full flow: patient not found → register → create reminder."""
    # find_patient: empty
    respx.get(f"{BASE_URL}/api/patients").mock(return_value=Response(200, json=[]))
    # register_patient
    respx.post(f"{BASE_URL}/api/patients").mock(
        return_value=Response(201, json={"id": "p-new", "cns": "111222333444555"})
    )
    # list_doctors
    respx.get(f"{BASE_URL}/api/doctors").mock(
        return_value=Response(200, json=[{"id": "d-001", "name": "DR. SILVA"}])
    )
    # find_reminder: not found
    respx.get(f"{BASE_URL}/api/reminders").mock(return_value=Response(200, json=[]))
    # create_reminder
    respx.post(f"{BASE_URL}/api/reminders").mock(return_value=Response(201, json={"id": "r-001"}))

    async with IntegrationPushClient(_make_system(), _make_endpoints()) as client:
        result = await client.process_appointment(_make_enriched_appointment())
        assert result.success is True
        assert result.patient_created is True
        assert result.reminder_created is True


@respx.mock
async def test_process_appointment_existing_patient_existing_reminder():
    """Full flow: patient found → reminder found → skip."""
    # find_patient: found
    respx.get(f"{BASE_URL}/api/patients").mock(
        return_value=Response(200, json=[{"id": "p-existing", "cns": "111222333444555"}])
    )
    # update_patient
    respx.put(url__regex=rf"{BASE_URL}/api/patients/.*").mock(
        return_value=Response(200, json={"id": "p-existing"})
    )
    # list_doctors
    respx.get(f"{BASE_URL}/api/doctors").mock(return_value=Response(200, json=[]))
    # find_reminder: found
    respx.get(f"{BASE_URL}/api/reminders").mock(
        return_value=Response(200, json=[{"id": "r-existing"}])
    )

    async with IntegrationPushClient(_make_system(), _make_endpoints()) as client:
        result = await client.process_appointment(_make_enriched_appointment())
        assert result.success is True
        assert result.reminder_skipped is True
        assert result.patient_updated is True


@respx.mock
async def test_process_appointment_missing_cns():
    """Missing CNS → error result."""
    appointment = _make_enriched_appointment()
    appointment["patient_cns"] = ""

    async with IntegrationPushClient(_make_system(), _make_endpoints()) as client:
        result = await client.process_appointment(appointment)
        assert result.success is False
        assert result.error == "Missing patient CNS"
