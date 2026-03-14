"""initial schema — 8 tables with seed data

Revision ID: 001
Revises: None
Create Date: 2026-03-15

Tables (FK dependency order):
1. system_types       (reference table, no FK)
2. users              (no FK)
3. systems            (FK: system_types)
4. user_selections    (FK: users)
5. system_profiles    (FK: system_types, systems)
6. system_endpoints   (FK: systems)
7. user_profiles      (FK: users, system_profiles)
8. credentials        (FK: users, system_profiles)

Seed data:
- 3 system_types (platform, regulation, integration)
- 6 systems (5 regulation + 1 integration)
- 18 system_profiles (3 SISREG + 12 regulation + 2 platform + 1 integration)
- 10 system_endpoints (4 SisReg WEB + 6 Saude AM Digital REST)
- 1 user (Alessandro)
- 17 user_profiles (Alessandro → all profiles)
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ── Fixed UUIDs ───────────────────────────────────────────────────────

PLATFORM_TYPE_ID = uuid.UUID("067dcf7e-d77d-4184-b712-9a9ecc9977fe")
REGULATION_TYPE_ID = uuid.UUID("dcd8e25e-5465-4a57-b1b7-3ceeec514aa6")
INTEGRATION_TYPE_ID = uuid.UUID("1ef85242-c2ee-4fc5-9e0d-725b5517f917")

SISREG_ID = uuid.UUID("22910218-c8b6-40fe-9e38-d971b609c155")
ESUS_ID = uuid.UUID("7006e8cd-5f14-4e86-8110-807bdc927ef2")
SIGA_ID = uuid.UUID("460c4245-b888-42a1-8802-76a64654a50a")
CARE_ID = uuid.UUID("967a3e71-d47b-4a3f-85ac-76e5e6818af6")
SER_ID = uuid.UUID("22dd0777-08fd-401a-b5f1-7a8cc73e0c41")
SAUDE_AM_DIGITAL_ID = uuid.UUID("a1b2c3d4-5e6f-7a8b-9c0d-e1f2a3b4c5d6")

ALESSANDRO_ID = uuid.UUID("b3a7c9e1-4f2d-4e8a-9c1b-5d6f7a8b9c0e")

# SISREG profiles — fixed UUIDs (credentials may reference them)
SISREG_VF_ID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000001")
SISREG_SOL_ID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000002")
SISREG_EXE_ID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000003")


def upgrade() -> None:
    # ── 1. system_types ───────────────────────────────────────────────
    op.create_table(
        "system_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_systype_code"),
    )

    # ── 2. users ──────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("login", sa.String(50), nullable=False),
        sa.Column("cpf", sa.String(14), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("login", name="uq_users_login"),
    )

    # ── 3. systems ────────────────────────────────────────────────────
    op.create_table(
        "systems",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("system_type_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        # Regulation-specific
        sa.Column("route_segment", sa.String(50), nullable=True),
        sa.Column("table_prefix", sa.String(20), nullable=True),
        # Integration-specific
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("state_name", sa.String(50), nullable=True),
        # Common
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_systems_code"),
        sa.ForeignKeyConstraint(["system_type_id"], ["system_types.id"], name="fk_systems_type", ondelete="RESTRICT"),
    )
    op.create_index("idx_systems_type", "systems", ["system_type_id"])
    op.execute(
        sa.text("CREATE UNIQUE INDEX uq_systems_table_prefix ON systems (table_prefix) WHERE table_prefix IS NOT NULL")
    )

    # ── 4. user_selections ────────────────────────────────────────────
    op.create_table(
        "user_selections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("system", sa.String(20), nullable=False),
        sa.Column("profile_type", sa.String(50), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("state_name", sa.String(50), nullable=False),
        sa.Column("selected_users", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "system", "profile_type", name="uq_sel_user_sys_prof"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_sel_user", ondelete="CASCADE"),
    )
    op.create_index("idx_sel_user", "user_selections", ["user_id"])

    # ── 5. system_profiles ────────────────────────────────────────────
    op.create_table(
        "system_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column("system_id", sa.Uuid(), nullable=True),
        sa.Column("profile_name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["scope_id"], ["system_types.id"], name="fk_sysprof_scope", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["system_id"], ["systems.id"], name="fk_sysprof_system", ondelete="RESTRICT"),
    )
    op.create_index("idx_sysprof_system", "system_profiles", ["system_id"])
    # Partial unique indexes
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_sysprof_system_name ON system_profiles "
            f"(system_id, profile_name) WHERE scope_id != '{PLATFORM_TYPE_ID}'"
        )
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_sysprof_plat ON system_profiles "
            f"(profile_name) WHERE scope_id = '{PLATFORM_TYPE_ID}'"
        )
    )

    # ── 6. system_endpoints ───────────────────────────────────────────
    op.create_table(
        "system_endpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("system_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("protocol", sa.String(10), nullable=False),
        sa.Column("http_method", sa.String(10), nullable=True),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("base_url_override", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("system_id", "name", name="uq_sysep_system_name"),
        sa.ForeignKeyConstraint(["system_id"], ["systems.id"], name="fk_sysep_system", ondelete="RESTRICT"),
    )
    op.create_index("idx_sysep_system", "system_endpoints", ["system_id"])

    # ── 7. user_profiles ──────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "profile_id", name="uq_usrprof_user_profile"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_usrprof_user", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["system_profiles.id"], name="fk_usrprof_profile", ondelete="RESTRICT"),
    )
    op.create_index("idx_usrprof_user", "user_profiles", ["user_id"])

    # ── 8. credentials ────────────────────────────────────────────────
    op.create_table(
        "credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("encrypted_password", sa.Text(), nullable=False),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("state_name", sa.String(50), nullable=True),
        sa.Column("unit_name", sa.String(200), nullable=True),
        sa.Column("unit_cnes", sa.String(7), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "profile_id", "username", name="uq_cred_user_profile_username"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_cred_user", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["system_profiles.id"], name="fk_cred_profile", ondelete="RESTRICT"),
    )
    op.create_index("idx_cred_user", "credentials", ["user_id"])
    op.create_index("idx_cred_profile", "credentials", ["profile_id"])

    # ══════════════════════════════════════════════════════════════════
    # SEED DATA
    # ══════════════════════════════════════════════════════════════════

    # ── system_types (3) ──────────────────────────────────────────────
    types_table = sa.table(
        "system_types",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        types_table,
        [
            {
                "id": PLATFORM_TYPE_ID,
                "code": "platform",
                "name": "Platform",
                "description": "RegulaHub platform-level (operator, administrator)",
                "sort_order": 0,
            },
            {
                "id": REGULATION_TYPE_ID,
                "code": "regulation",
                "name": "Regulation",
                "description": "External regulation systems (SisReg, e-SUS, SIGA, CARE, SER)",
                "sort_order": 1,
            },
            {
                "id": INTEGRATION_TYPE_ID,
                "code": "integration",
                "name": "Integration",
                "description": "Destination platforms for processed data (Saude AM Digital, etc.)",
                "sort_order": 2,
            },
        ],
    )

    # ── users (1) ─────────────────────────────────────────────────────
    users_table = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String),
        sa.column("email", sa.String),
        sa.column("login", sa.String),
    )
    op.bulk_insert(
        users_table,
        [
            {
                "id": ALESSANDRO_ID,
                "name": "Alessandro",
                "email": "alessandro@regulahub.local",
                "login": "alessandro",
            },
        ],
    )

    # ── systems (6) ───────────────────────────────────────────────────
    systems_table = sa.table(
        "systems",
        sa.column("id", sa.Uuid()),
        sa.column("system_type_id", sa.Uuid()),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("base_url", sa.String),
        sa.column("icon", sa.String),
        sa.column("route_segment", sa.String),
        sa.column("table_prefix", sa.String),
        sa.column("category", sa.String),
        sa.column("state", sa.String),
        sa.column("state_name", sa.String),
        sa.column("created_by", sa.Uuid()),
    )
    op.bulk_insert(
        systems_table,
        [
            # 5 regulation systems
            {
                "id": SISREG_ID,
                "system_type_id": REGULATION_TYPE_ID,
                "code": "SISREG",
                "name": "SisReg",
                "description": "Sistema Nacional de Regulação do SUS",
                "base_url": "https://sisregiii.saude.gov.br",
                "icon": "Monitor",
                "route_segment": "sisreg",
                "table_prefix": "sisreg",
                "category": None,
                "state": None,
                "state_name": None,
                "created_by": None,
            },
            {
                "id": ESUS_ID,
                "system_type_id": REGULATION_TYPE_ID,
                "code": "ESUS",
                "name": "e-SUS Regulação",
                "description": "e-SUS Atenção Básica — módulo de regulação",
                "base_url": None,
                "icon": "ArrowLeftRight",
                "route_segment": "esus-regulacao",
                "table_prefix": "esus",
                "category": None,
                "state": None,
                "state_name": None,
                "created_by": None,
            },
            {
                "id": SIGA_ID,
                "system_type_id": REGULATION_TYPE_ID,
                "code": "SIGA",
                "name": "SIGA Saúde",
                "description": "Sistema Integrado de Gestão e Assistência à Saúde (SP)",
                "base_url": None,
                "icon": "Hospital",
                "route_segment": "siga-saude",
                "table_prefix": "siga",
                "category": None,
                "state": None,
                "state_name": None,
                "created_by": None,
            },
            {
                "id": CARE_ID,
                "system_type_id": REGULATION_TYPE_ID,
                "code": "CARE",
                "name": "Care Paraná",
                "description": "Sistema de regulação do estado do Paraná",
                "base_url": None,
                "icon": "Heart",
                "route_segment": "care-parana",
                "table_prefix": "care",
                "category": None,
                "state": None,
                "state_name": None,
                "created_by": None,
            },
            {
                "id": SER_ID,
                "system_type_id": REGULATION_TYPE_ID,
                "code": "SER",
                "name": "SER (RJ)",
                "description": "Sistema Estadual de Regulação do Rio de Janeiro",
                "base_url": None,
                "icon": "Landmark",
                "route_segment": "ser-rj",
                "table_prefix": "ser",
                "category": None,
                "state": None,
                "state_name": None,
                "created_by": None,
            },
            # 1 integration system
            {
                "id": SAUDE_AM_DIGITAL_ID,
                "system_type_id": INTEGRATION_TYPE_ID,
                "code": "SAUDE_AM_DIGITAL",
                "name": "Saúde AM Digital",
                "description": "Plataforma de teleconsulta do estado do Amazonas",
                "base_url": None,
                "icon": "Stethoscope",
                "route_segment": None,
                "table_prefix": None,
                "category": "teleconsultation",
                "state": "AM",
                "state_name": "Amazonas",
                "created_by": ALESSANDRO_ID,
            },
        ],
    )

    # ── system_profiles (18) ──────────────────────────────────────────
    profiles_table = sa.table(
        "system_profiles",
        sa.column("id", sa.Uuid()),
        sa.column("scope_id", sa.Uuid()),
        sa.column("system_id", sa.Uuid()),
        sa.column("profile_name", sa.String),
        sa.column("description", sa.Text),
        sa.column("level", sa.Integer),
        sa.column("sort_order", sa.Integer),
    )

    profiles_data = [
        # SISREG (3 fixed UUIDs)
        {
            "id": SISREG_VF_ID,
            "scope_id": REGULATION_TYPE_ID,
            "system_id": SISREG_ID,
            "profile_name": "VIDEOFONISTA",
            "description": "State-wide view — lists all appointments",
            "level": 0,
            "sort_order": 0,
        },
        {
            "id": SISREG_SOL_ID,
            "scope_id": REGULATION_TYPE_ID,
            "system_id": SISREG_ID,
            "profile_name": "SOLICITANTE",
            "description": "Unit-scoped view — requires operator selection",
            "level": 0,
            "sort_order": 1,
        },
        {
            "id": SISREG_EXE_ID,
            "scope_id": REGULATION_TYPE_ID,
            "system_id": SISREG_ID,
            "profile_name": "EXECUTANTE/SOLICITANTE",
            "description": "Executing and requesting unit view",
            "level": 0,
            "sort_order": 2,
        },
        # ESUS (3)
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": ESUS_ID,
            "profile_name": "REGULADOR",
            "description": "Regulator — reviews and approves regulation requests",
            "level": 0,
            "sort_order": 0,
        },
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": ESUS_ID,
            "profile_name": "SOLICITANTE",
            "description": "Requester — creates requests from primary care units",
            "level": 0,
            "sort_order": 1,
        },
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": ESUS_ID,
            "profile_name": "EXECUTANTE",
            "description": "Executor — manages approved requests at executing unit",
            "level": 0,
            "sort_order": 2,
        },
        # SIGA (3)
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": SIGA_ID,
            "profile_name": "REGULADOR",
            "description": "Regulator — manages queues and approvals (SP municipality)",
            "level": 0,
            "sort_order": 0,
        },
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": SIGA_ID,
            "profile_name": "SOLICITANTE",
            "description": "Requester — creates requests from SP health units",
            "level": 0,
            "sort_order": 1,
        },
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": SIGA_ID,
            "profile_name": "GESTOR",
            "description": "Manager — administrative oversight and reporting",
            "level": 0,
            "sort_order": 2,
        },
        # CARE (3)
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": CARE_ID,
            "profile_name": "REGULADOR",
            "description": "Regulator — approves or redirects requests (PR state)",
            "level": 0,
            "sort_order": 0,
        },
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": CARE_ID,
            "profile_name": "SOLICITANTE",
            "description": "Requester — creates requests from units",
            "level": 0,
            "sort_order": 1,
        },
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": CARE_ID,
            "profile_name": "AUDITOR",
            "description": "Auditor — read-only access for audit purposes",
            "level": 0,
            "sort_order": 2,
        },
        # SER (3)
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": SER_ID,
            "profile_name": "REGULADOR",
            "description": "Regulator — central state regulation (RJ)",
            "level": 0,
            "sort_order": 0,
        },
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": SER_ID,
            "profile_name": "SOLICITANTE",
            "description": "Requester — unit-level request creation",
            "level": 0,
            "sort_order": 1,
        },
        {
            "id": uuid.uuid4(),
            "scope_id": REGULATION_TYPE_ID,
            "system_id": SER_ID,
            "profile_name": "EXECUTOR",
            "description": "Executor — receiving unit for approved requests",
            "level": 0,
            "sort_order": 2,
        },
        # Platform (2)
        {
            "id": uuid.uuid4(),
            "scope_id": PLATFORM_TYPE_ID,
            "system_id": None,
            "profile_name": "OPERATOR",
            "description": "Operational user — runs daily workflows",
            "level": 0,
            "sort_order": 0,
        },
        {
            "id": uuid.uuid4(),
            "scope_id": PLATFORM_TYPE_ID,
            "system_id": None,
            "profile_name": "ADMINISTRATOR",
            "description": "Admin — manages users and configuration",
            "level": 1,
            "sort_order": 1,
        },
        # Integration — Saude AM Digital (1)
        {
            "id": uuid.uuid4(),
            "scope_id": INTEGRATION_TYPE_ID,
            "system_id": SAUDE_AM_DIGITAL_ID,
            "profile_name": "API_CLIENT",
            "description": "API access for Saude AM Digital integration",
            "level": 0,
            "sort_order": 0,
        },
    ]
    op.bulk_insert(profiles_table, profiles_data)

    # ── system_endpoints (10) ─────────────────────────────────────────
    endpoints_table = sa.table(
        "system_endpoints",
        sa.column("id", sa.Uuid()),
        sa.column("system_id", sa.Uuid()),
        sa.column("name", sa.String),
        sa.column("protocol", sa.String),
        sa.column("http_method", sa.String),
        sa.column("path", sa.String),
        sa.column("config", sa.JSON),
        sa.column("sort_order", sa.Integer),
        sa.column("created_by", sa.Uuid()),
    )
    op.bulk_insert(
        endpoints_table,
        [
            # SisReg WEB endpoints (4)
            {
                "id": uuid.uuid4(),
                "system_id": SISREG_ID,
                "name": "login",
                "protocol": "WEB",
                "http_method": "POST",
                "path": "/",
                "config": {"form_fields": {"usuario": "username", "senha_256": "password_hash", "etapa": "ACESSO"}},
                "sort_order": 0,
                "created_by": ALESSANDRO_ID,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SISREG_ID,
                "name": "scheduling_menu",
                "protocol": "WEB",
                "http_method": "GET",
                "path": "/sisreg/operador_solicitacao",
                "config": {"css_selectors": {"menu_item": "li:nth-child(3) a"}},
                "sort_order": 1,
                "created_by": ALESSANDRO_ID,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SISREG_ID,
                "name": "search_appointments",
                "protocol": "WEB",
                "http_method": "GET",
                "path": "/cgi-bin/gerenciador_solicitacao",
                "config": {"query_params": {"etapa": "PESQUISAR"}},
                "sort_order": 2,
                "created_by": ALESSANDRO_ID,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SISREG_ID,
                "name": "appointment_detail",
                "protocol": "WEB",
                "http_method": "GET",
                "path": "/cgi-bin/gerenciador_solicitacao",
                "config": {"query_params": {"etapa": "VISUALIZAR_FICHA"}},
                "sort_order": 3,
                "created_by": ALESSANDRO_ID,
            },
            # Saude AM Digital REST endpoints (6)
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "register_patient",
                "protocol": "REST",
                "http_method": "POST",
                "path": "/api/patients",
                "config": {"auth_pattern": "api_key", "host_hint": "auth"},
                "sort_order": 0,
                "created_by": ALESSANDRO_ID,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "find_patient",
                "protocol": "REST",
                "http_method": "GET",
                "path": "/api/patients",
                "config": {"auth_pattern": "api_key"},
                "sort_order": 1,
                "created_by": ALESSANDRO_ID,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "update_patient",
                "protocol": "REST",
                "http_method": "PUT",
                "path": "/api/patients/{id}",
                "config": {"auth_pattern": "api_key"},
                "sort_order": 2,
                "created_by": ALESSANDRO_ID,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "list_doctors",
                "protocol": "REST",
                "http_method": "GET",
                "path": "/api/doctors",
                "config": {"auth_pattern": "api_key"},
                "sort_order": 3,
                "created_by": ALESSANDRO_ID,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "find_reminder",
                "protocol": "REST",
                "http_method": "GET",
                "path": "/api/reminders",
                "config": {"auth_pattern": "api_key"},
                "sort_order": 4,
                "created_by": ALESSANDRO_ID,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "create_reminder",
                "protocol": "REST",
                "http_method": "POST",
                "path": "/api/reminders",
                "config": {"auth_pattern": "api_key"},
                "sort_order": 5,
                "created_by": ALESSANDRO_ID,
            },
        ],
    )

    # ── user_profiles (17) — Alessandro → all profiles ────────────────
    user_profiles_table = sa.table(
        "user_profiles",
        sa.column("id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("profile_id", sa.Uuid()),
    )
    # Assign Alessandro to all profiles except the integration API_CLIENT (last one)
    user_profile_rows = [
        {"id": uuid.uuid4(), "user_id": ALESSANDRO_ID, "profile_id": p["id"]}
        for p in profiles_data[:-1]  # skip API_CLIENT — integration-level, no user assignment
    ]
    op.bulk_insert(user_profiles_table, user_profile_rows)


def downgrade() -> None:
    op.drop_table("credentials")
    op.drop_table("user_profiles")
    op.drop_table("system_endpoints")
    op.drop_table("system_profiles")
    op.drop_table("user_selections")
    op.drop_table("systems")
    op.drop_table("users")
    op.drop_table("system_types")
