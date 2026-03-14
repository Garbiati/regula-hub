"""Pydantic schemas for Absens-compatible API responses.

These schemas replicate the exact JSON contract that ptm-regulation-service (.NET 9)
expects from the Absens API, enabling a drop-in URL replacement.
"""

from pydantic import BaseModel, ConfigDict, Field


class PatientPhoneResponse(BaseModel):
    """Phone DTO matching the .NET PhoneDto contract."""

    model_config = ConfigDict(populate_by_name=True)

    ddd: str = ""
    number: str = ""


class DepartmentSolicitationInfosResponse(BaseModel):
    """Department info DTO matching the .NET DeptInfoDto contract."""

    model_config = ConfigDict(populate_by_name=True)

    cnes: str = ""
    department: str = ""


class AbsensAppointmentResponse(BaseModel):
    """Appointment listing DTO matching the .NET AppointmentDTO contract.

    All required string fields default to "" (never null) to avoid
    System.Text.Json deserialization exceptions on the .NET side.
    """

    model_config = ConfigDict(populate_by_name=True)

    cod: str = ""
    patient_birthday: str = Field(default="", alias="patientBirthday")
    patient_mother_name: str = Field(default="", alias="patientMotherName")
    department_execute: str = Field(default="", alias="departmentExecute")
    department_solicitation: str = Field(default="", alias="departmentSolicitation")
    procedure: str = ""
    status_sisreg: str | None = Field(default=None, alias="statusSisreg")


class AbsensDetailResponse(BaseModel):
    """Appointment detail DTO matching the .NET DetailsAppointmentDTO contract.

    All required string fields default to "" (never null).
    Nullable fields default to None.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    cod: str = ""
    confirmation_key: str = Field(default="", alias="confirmationKey")
    patient: str = ""
    patient_cpf: str | None = Field(default=None, alias="patientCPF")
    cns: str = ""
    patient_phones: list[PatientPhoneResponse] | None = Field(default=None, alias="patientPhones")
    department_solicitation: str = Field(default="", alias="departmentSolicitation")
    department_execute: str = Field(default="", alias="departmentExecute")
    appointment_date_timestamp: str | None = Field(default=None, alias="appointmentDateTimestamp")
    appointment_date: str = Field(default="", alias="appointmentDate")
    status_sisreg: str = Field(default="", alias="statusSisreg")
    doctor_execute: str = Field(default="", alias="doctorExecute")
    status: str = ""
    best_phone: PatientPhoneResponse | None = Field(default=None, alias="bestPhone")
    department_solicitation_infos: DepartmentSolicitationInfosResponse | None = Field(
        default=None, alias="departmentSolicitationInfos"
    )
