"""Pydantic models for SisReg data."""

import re

from pydantic import BaseModel, Field, field_validator


class SearchFilters(BaseModel):
    # Identification
    sol_code: str | None = Field(None, max_length=20)
    patient_cns: str | None = Field(None, max_length=20)
    patient_name: str | None = Field(None, max_length=200)
    cnes_solicitation: str | None = Field(None, max_length=20)
    cnes_execute: str | None = Field(None, max_length=20)
    # Procedure
    procedure_unified_code: str | None = Field(None, max_length=20)
    procedure_internal_code: str | None = Field(None, max_length=20)
    procedure_description: str | None = Field(None, max_length=200)
    # Date/Period
    search_type: str = Field("agendamento", max_length=20)
    date_from: str = Field(..., min_length=10, max_length=10, description="dd/MM/yyyy")
    date_to: str = Field(..., min_length=10, max_length=10, description="dd/MM/yyyy")
    # Status
    situation: str = Field("9", max_length=10)
    items_per_page: str = Field("0", max_length=10)
    # Auth context
    profile_type: str = Field(..., min_length=1, max_length=50)
    usernames: list[str] = Field(..., min_length=1, description="One or more operator usernames")

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", v):
            raise ValueError("Date must match dd/MM/yyyy format")
        return v

    @field_validator("situation")
    @classmethod
    def validate_situation(cls, v: str) -> str:
        valid = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"}
        if v not in valid:
            raise ValueError(f"Invalid situation '{v}', must be one of {sorted(valid, key=int)}")
        return v

    @field_validator("items_per_page")
    @classmethod
    def validate_items_per_page(cls, v: str) -> str:
        valid = {"0", "10", "20", "50", "100"}
        if v not in valid:
            raise ValueError(f"Invalid items_per_page '{v}', must be one of {sorted(valid, key=int)}")
        return v


class AppointmentListing(BaseModel):
    code: str
    request_date: str
    risk: int = 0
    patient_name: str
    phone: str = ""
    municipality: str = ""
    age: str = ""
    procedure: str = ""
    cid: str = ""
    dept_solicitation: str = ""
    dept_execute: str = ""
    execution_date: str = ""
    status: str = ""


class BestPhone(BaseModel):
    raw: str
    ddd: str = ""
    number: str = ""
    phone_type: str = ""  # "mobile" or "landline"


class AppointmentDetail(BaseModel):
    # Confirmation key (tbody 1)
    confirmation_key: str | None = None
    # Requesting unit (tbody 2)
    req_unit_name: str | None = None
    req_unit_cnes: str | None = None
    solicitation_operator: str | None = None
    videocall_operator: str | None = None
    # Executing unit (tbody 3) — critical for integration routing
    exec_unit_name: str | None = None
    exec_unit_cnes: str | None = None
    exec_unit_authorizer: str | None = None
    exec_unit_slot: str | None = None
    exec_unit_address: str | None = None
    exec_unit_address_number: str | None = None
    exec_unit_address_complement: str | None = None
    exec_unit_approval_date: str | None = None
    exec_unit_phone: str | None = None
    exec_unit_cep: str | None = None
    exec_unit_neighborhood: str | None = None
    exec_unit_municipality: str | None = None
    exec_unit_professional: str | None = None
    exec_unit_appointment_datetime: str | None = None
    # Patient (tbody 4)
    patient_cns: str | None = None
    patient_name: str | None = None
    patient_birth_date: str | None = None
    patient_phone: str | None = None
    # Justification (tbody 6)
    justification: str | None = None
    # Solicitation (tbody 9)
    sol_code: str | None = None
    sol_status: str | None = None
    sol_doctor_cpf: str | None = None
    sol_doctor_crm: str | None = None
    sol_doctor_name: str | None = None
    sol_cid: str | None = None
    sol_risk: str | None = None
    sol_regulatory_center: str | None = None
    # Procedure (tbody 11)
    procedure_name: str | None = None
    procedure_code: str | None = None
    # Phone
    best_phone: BestPhone | None = None


class CadwebPatientData(BaseModel):
    """Patient demographics from CadWeb (Consulta CNS)."""

    cpf: str | None = None
    mother_name: str | None = None
    father_name: str | None = None
    sex: str | None = None
    phone_type: str | None = None  # "CELULAR", "RESIDENCIAL", etc.
    phone_ddd: str | None = None
    phone_number: str | None = None


class SearchResponse(BaseModel):
    items: list[AppointmentListing]
    total: int


class OperatorSearchResponse(BaseModel):
    operator: str
    items: list[AppointmentListing]
    total: int


# ── Schedule export models ────────────────────────────────────────────────────


class ExportFilters(BaseModel):
    """Filters for the SisReg schedule export endpoint."""

    date_from: str = Field(..., min_length=10, max_length=10, description="dd/MM/yyyy")
    date_to: str = Field(..., min_length=10, max_length=10, description="dd/MM/yyyy")
    cpf: str = Field("0", max_length=20, description="Professional CPF, '0' for all")
    procedimento: str = Field("", max_length=200, description="Procedure code, empty for all")
    file_type: int = Field(1, ge=0, le=1, description="0=TXT, 1=CSV")
    profile_type: str = Field("SOLICITANTE", min_length=1, max_length=50)
    usernames: list[str] = Field(..., min_length=1, description="One or more operator usernames")

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", v):
            raise ValueError("Date must match dd/MM/yyyy format")
        return v


class ScheduleExportRow(BaseModel):
    """A single row from the SisReg schedule export CSV (38 columns)."""

    solicitacao: str = ""
    codigo_interno: str = ""
    codigo_unificado: str = ""
    descricao_procedimento: str = ""
    cpf_proficional_executante: str = ""  # Intentional typo — matches SisReg CSV header
    nome_profissional_executante: str = ""
    data_agendamento: str = ""
    hr_agendamento: str = ""
    tipo: str = ""
    cns: str = ""
    nome: str = ""
    dt_nascimento: str = ""
    idade: str = ""
    idade_meses: str = ""
    nome_mae: str = ""
    tipo_logradouro: str = ""
    logradouro: str = ""
    complemento: str = ""
    numero_logradouro: str = ""
    bairro: str = ""
    cep: str = ""
    telefone: str = ""
    municipio: str = ""
    ibge: str = ""
    mun_solicitante: str = ""
    ibge_solicitante: str = ""
    cnes_solicitante: str = ""
    unidade_fantasia: str = ""
    sexo: str = ""
    data_solicitacao: str = ""
    operador_solicitante: str = ""
    data_autorizacao: str = ""
    operador_autorizador: str = ""
    valor_procedimento: str = ""
    situacao: str = ""
    cid: str = ""
    cpf_profissional_solicitante: str = ""
    nome_profissional_solicitante: str = ""


class ScheduleExportResponse(BaseModel):
    """Aggregated response from multi-operator schedule export."""

    items: list[ScheduleExportRow]
    total: int
    operators_queried: int
    operators_succeeded: int


class EnrichedExportRow(ScheduleExportRow):
    """ScheduleExportRow with additional fields from CADSUS."""

    cpf_paciente: str | None = None
    email_paciente: str | None = None
    telefone_cadsus: str | None = None
    nome_pai: str | None = None
    raca: str | None = None
    cns_definitivo: str | None = None
