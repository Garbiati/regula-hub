"""Admin API response schemas."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Credential schemas
# ---------------------------------------------------------------------------


class AdminCredentialCreate(BaseModel):
    user_id: uuid.UUID
    profile_id: uuid.UUID
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)
    state: str | None = Field(None, min_length=2, max_length=2)
    state_name: str | None = Field(None, max_length=100)
    unit_name: str | None = Field(None, max_length=200)
    unit_cnes: str | None = Field(None, max_length=20)


class AdminCredentialUpdate(BaseModel):
    username: str | None = Field(None, min_length=1, max_length=100)
    password: str | None = Field(None, min_length=1, max_length=200)
    profile_id: uuid.UUID | None = None
    state: str | None = Field(None, min_length=2, max_length=2)
    state_name: str | None = Field(None, max_length=100)
    unit_name: str | None = Field(None, max_length=200)
    unit_cnes: str | None = Field(None, max_length=20)
    is_active: bool | None = None


class AdminCredentialItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    profile_id: uuid.UUID
    username: str
    profile_name: str | None = None
    system_code: str | None = None
    scope: str | None = None
    state: str | None = None
    state_name: str | None = None
    unit_name: str | None = None
    unit_cnes: str | None = None
    is_active: bool
    last_validated_at: datetime | None = None
    is_valid: bool | None = None
    created_at: datetime
    updated_at: datetime | None = None
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class AdminCredentialListResponse(BaseModel):
    items: list[AdminCredentialItem]
    total: int


class AdminCredentialValidationItem(BaseModel):
    username: str
    valid: bool
    error: str | None = None


class AdminStateItem(BaseModel):
    state: str
    state_name: str


class AdminProfileItem(BaseModel):
    name: str
    description: str


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class AdminUserItem(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    login: str
    cpf: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    items: list[AdminUserItem]
    total: int


class AdminUserSelectionItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    system: str
    profile_type: str
    state: str
    state_name: str
    selected_users: list[str]
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminUserSelectionListResponse(BaseModel):
    items: list[AdminUserSelectionItem]
    total: int


class AdminUpsertSelectionRequest(BaseModel):
    system: str = Field(..., min_length=1, max_length=20)
    profile_type: str = Field(..., min_length=1, max_length=50)
    state: str = Field(..., min_length=2, max_length=2)
    state_name: str = Field(..., min_length=1, max_length=100)
    selected_users: list[str]


# ---------------------------------------------------------------------------
# Regulation system schemas
# ---------------------------------------------------------------------------


class AdminRegulationSystemItem(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    base_url: str | None = None
    route_segment: str | None = None
    icon: str | None = None
    table_prefix: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class AdminRegulationSystemListResponse(BaseModel):
    items: list[AdminRegulationSystemItem]
    total: int


class AdminRegulationSystemCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    base_url: str | None = Field(None, max_length=500)
    route_segment: str | None = Field(None, max_length=50)
    icon: str | None = Field(None, max_length=50)
    table_prefix: str = Field(..., min_length=1, max_length=20)


class AdminRegulationSystemUpdate(BaseModel):
    code: str | None = Field(None, min_length=1, max_length=20)
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    base_url: str | None = Field(None, max_length=500)
    route_segment: str | None = Field(None, max_length=50)
    icon: str | None = Field(None, max_length=50)
    is_active: bool | None = None


class AdminSystemProfileItem(BaseModel):
    id: uuid.UUID
    scope: str
    system_id: uuid.UUID | None = None
    system_code: str | None = None
    profile_name: str
    description: str | None = None
    level: int = 0
    sort_order: int = 0
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None


class AdminSystemProfileListResponse(BaseModel):
    items: list[AdminSystemProfileItem]
    total: int


class AdminSystemProfileCreate(BaseModel):
    profile_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    sort_order: int = 0


class AdminSystemProfileUpdate(BaseModel):
    profile_name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    sort_order: int | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Form metadata schemas
# ---------------------------------------------------------------------------


class FormOptionItem(BaseModel):
    value: str = Field(..., min_length=1, max_length=50)
    label: str | None = Field(None, max_length=200)
    label_key: str | None = Field(None, max_length=100)
    canonical_label: str | None = Field(None, max_length=200)
    is_default: bool | None = None
    applies_to: list[str] | None = None


class FormMetadataDefaults(BaseModel):
    search_type: str = "agendamento"
    situation: str = "7"
    items_per_page: str = "20"


class FormMetadataResponse(BaseModel):
    version: int
    updated_at: str | None = None
    search_types: list[FormOptionItem]
    situations: list[FormOptionItem]
    items_per_page: list[FormOptionItem]
    defaults: FormMetadataDefaults


class FormMetadataUpdate(BaseModel):
    version: int | None = None
    search_types: list[FormOptionItem] | None = None
    situations: list[FormOptionItem] | None = None
    items_per_page: list[FormOptionItem] | None = None
    defaults: FormMetadataDefaults | None = None


# ---------------------------------------------------------------------------
# Schedule export schemas
# ---------------------------------------------------------------------------


class ScheduleExportRequest(BaseModel):
    date_from: str = Field(..., min_length=10, max_length=10, description="dd/MM/yyyy")
    date_to: str = Field(..., min_length=10, max_length=10, description="dd/MM/yyyy")
    profile_type: str = Field("SOLICITANTE", min_length=1, max_length=50)
    usernames: list[str] = Field(..., min_length=1)
    procedure_filter: str | None = Field(None, max_length=200, description="Filter by descricao_procedimento")
    enrich: bool = Field(False, description="Enrich with CADSUS data")
    persist: bool = Field(False, description="Enable persistent cache")

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", v):
            raise ValueError("Date must match dd/MM/yyyy format")
        return v


class ScheduleExportItemResponse(BaseModel):
    solicitacao: str
    codigo_interno: str = ""
    codigo_unificado: str = ""
    descricao_procedimento: str = ""
    nome_profissional_executante: str = ""
    data_agendamento: str = ""
    hr_agendamento: str = ""
    tipo: str = ""
    cns: str = ""
    nome: str = ""
    dt_nascimento: str = ""
    idade: str = ""
    nome_mae: str = ""
    telefone: str = ""
    municipio: str = ""
    cnes_solicitante: str = ""
    unidade_fantasia: str = ""
    sexo: str = ""
    data_solicitacao: str = ""
    situacao: str = ""
    cid: str = ""
    nome_profissional_solicitante: str = ""


class ScheduleExportListResponse(BaseModel):
    items: list[ScheduleExportItemResponse]
    total: int
    operators_queried: int
    operators_succeeded: int


class OperatorScheduleExportResponse(BaseModel):
    operator: str
    items: list[ScheduleExportItemResponse]
    total: int


class CadsusPatientEnrichment(BaseModel):
    cpf: str | None = None
    email: str | None = None
    phone: str | None = None
    father_name: str | None = None
    race: str | None = None
    cns_definitivo: str | None = None


class CadsusEnrichRequest(BaseModel):
    cns_list: list[str] = Field(..., min_length=1, max_length=5000)
    # Fallback phone from export CSV — keyed by CNS, used when CADSUS has no phone
    phone_fallbacks: dict[str, str] = Field(default_factory=dict)
    # SisReg CadWeb fallback (optional) — used when CADSUS fails for some CNS
    sisreg_username: str | None = Field(None, max_length=100)
    sisreg_profile_type: str | None = Field(None, max_length=50)


class CadsusEnrichResponse(BaseModel):
    results: dict[str, CadsusPatientEnrichment]
    total: int
    found: int
    failed: int
    fallback_found: int = 0
    from_cache: int = 0


class EnrichedExportItemResponse(ScheduleExportItemResponse):
    cpf_paciente: str | None = None
    email_paciente: str | None = None
    telefone_cadsus: str | None = None
    nome_pai: str | None = None
    raca: str | None = None
    cns_definitivo: str | None = None


class EnrichedExportListResponse(BaseModel):
    items: list[EnrichedExportItemResponse]
    total: int
    total_unfiltered: int | None = None
    operators_queried: int
    operators_succeeded: int
    enriched_count: int = 0
    procedure_filter: str | None = None


# ---------------------------------------------------------------------------
# Cached export schemas
# ---------------------------------------------------------------------------


class CachedExportQueryRequest(BaseModel):
    date_from: str = Field(..., min_length=10, max_length=10, description="dd/MM/yyyy")
    date_to: str = Field(..., min_length=10, max_length=10, description="dd/MM/yyyy")
    procedure_filter: str | None = Field(None, max_length=200)

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", v):
            raise ValueError("Date must match dd/MM/yyyy format")
        return v


class CachedExportResponse(BaseModel):
    items: list[EnrichedExportItemResponse]
    total: int


class PersistExportRequest(BaseModel):
    items: list[EnrichedExportItemResponse] = Field(..., max_length=10000)


class PersistExportResponse(BaseModel):
    persisted: int
