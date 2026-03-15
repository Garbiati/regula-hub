"""Tests for Absens-compatible Pydantic schemas."""

from regulahub.api.controllers.compat.absens_schemas import (
    AbsensAppointmentResponse,
    AbsensDetailResponse,
    DepartmentSolicitationInfosResponse,
    PatientPhoneResponse,
)


class TestAbsensAppointmentResponse:
    def test_default_keys_camel_case(self):
        """T1: model_dump(by_alias=True) produces the exact camelCase keys."""
        data = AbsensAppointmentResponse().model_dump(by_alias=True)
        expected_keys = sorted(
            [
                "cod",
                "patientBirthday",
                "patientMotherName",
                "departmentExecute",
                "departmentSolicitation",
                "procedure",
                "statusSisreg",
            ]
        )
        assert sorted(data.keys()) == expected_keys

    def test_required_strings_default_empty(self):
        """T2: Required string fields default to '' not None."""
        resp = AbsensAppointmentResponse()
        assert resp.cod == ""
        assert resp.patient_birthday == ""
        assert resp.patient_mother_name == ""
        assert resp.department_execute == ""
        assert resp.department_solicitation == ""
        assert resp.procedure == ""

    def test_nullable_defaults_to_none(self):
        """T2b: Nullable fields default to None."""
        resp = AbsensAppointmentResponse()
        assert resp.status_sisreg is None


class TestAbsensDetailResponse:
    def test_serializes_with_real_data(self):
        """T3: Detail with real data serializes correctly."""
        phone = PatientPhoneResponse(ddd="92", number="98765-4321")
        resp = AbsensDetailResponse(
            cod="12345",
            confirmation_key="CONF-ABC-123",
            cns="898001234567890",
            patient_phones=[phone],
            best_phone=phone,
            appointment_date="QUA ● 20/03/2026 ● 14h00min",
        )
        data = resp.model_dump(by_alias=True)
        assert data["cod"] == "12345"
        assert data["confirmationKey"] == "CONF-ABC-123"
        assert data["cns"] == "898001234567890"
        assert data["patientPhones"] == [{"ddd": "92", "number": "98765-4321"}]
        assert data["bestPhone"] == {"ddd": "92", "number": "98765-4321"}
        assert data["appointmentDate"] == "QUA ● 20/03/2026 ● 14h00min"

    def test_exact_16_keys(self):
        """T5: Detail JSON has exactly the 16 expected fields."""
        data = AbsensDetailResponse().model_dump(by_alias=True)
        expected_keys = sorted(
            [
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
            ]
        )
        assert sorted(data.keys()) == expected_keys
        assert len(data) == 16  # 16 fields (id through departmentSolicitationInfos)


class TestDepartmentSolicitationInfosResponse:
    def test_serialization(self):
        """T6: DepartmentSolicitationInfosResponse serializes correctly."""
        info = DepartmentSolicitationInfosResponse(cnes="1234567", department="UBS CENTRO")
        data = info.model_dump(by_alias=True)
        assert data == {"cnes": "1234567", "department": "UBS CENTRO"}

    def test_defaults_empty(self):
        """T7: DepartmentSolicitationInfosResponse defaults to empty strings."""
        info = DepartmentSolicitationInfosResponse()
        data = info.model_dump(by_alias=True)
        assert data["cnes"] == ""
        assert data["department"] == ""


class TestPatientPhoneResponse:
    def test_serialization(self):
        """T4: Phone DTO serializes correctly."""
        phone = PatientPhoneResponse(ddd="92", number="98765-4321")
        data = phone.model_dump(by_alias=True)
        assert data == {"ddd": "92", "number": "98765-4321"}
