"""integration mapping tables and endpoint corrections for Saude AM Digital

Revision ID: 006
Revises: 005
Create Date: 2026-03-22

Creates three integration mapping tables:
1. integration_departments — health unit departments with CNES codes
2. integration_procedures — teleconsultation procedures by specialty
3. integration_execution_mappings — requester-to-executor CNES mappings

Also corrects the system_endpoints for SAUDE_AM_DIGITAL:
deletes the 6 placeholder endpoints from migration 001 and inserts the
7 correct REST endpoints with proper paths and base_url_override.
"""

import json
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SAUDE_AM_DIGITAL_ID = uuid.UUID("a1b2c3d4-5e6f-7a8b-9c0d-e1f2a3b4c5d6")

# ── Endpoint config shared by all Saude AM Digital endpoints ──────────
ENDPOINT_CONFIG = json.dumps({"auth_type": "api_key", "headers": {"PTM-Client-Domain": "SAUDEAMDIGITAL"}})


def upgrade() -> None:
    # ══════════════════════════════════════════════════════════════════
    # TABLE CREATION
    # ══════════════════════════════════════════════════════════════════

    # ── 1. integration_departments ────────────────────────────────────
    op.create_table(
        "integration_departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("integration_system_id", sa.Uuid(), nullable=False),
        sa.Column("department_name", sa.String(200), nullable=False),
        sa.Column("cnes_code", sa.String(10), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("department_type", sa.String(30), nullable=False),
        sa.Column("is_remote", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cnes_code", name="uq_integ_dept_cnes"),
        sa.ForeignKeyConstraint(
            ["integration_system_id"],
            ["systems.id"],
            name="fk_integ_dept_system",
            ondelete="RESTRICT",
        ),
    )

    op.create_index("idx_integ_dept_system", "integration_departments", ["integration_system_id"])
    op.create_index("idx_integ_dept_cnes", "integration_departments", ["cnes_code"])

    # ── 2. integration_procedures ─────────────────────────────────────
    op.create_table(
        "integration_procedures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("integration_system_id", sa.Uuid(), nullable=False),
        sa.Column("procedure_name", sa.String(300), nullable=False),
        sa.Column("specialty_name", sa.String(100), nullable=False),
        sa.Column("specialty_id", sa.Integer(), nullable=False),
        sa.Column("work_scale_name", sa.String(100), nullable=False),
        sa.Column("work_scale_id", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["integration_system_id"],
            ["systems.id"],
            name="fk_integ_proc_system",
            ondelete="RESTRICT",
        ),
    )

    op.create_index("idx_integ_proc_system", "integration_procedures", ["integration_system_id"])

    # ── 3. integration_execution_mappings ──────────────────────────────
    op.create_table(
        "integration_execution_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("integration_system_id", sa.Uuid(), nullable=False),
        sa.Column("municipality", sa.String(100), nullable=False),
        sa.Column("requester_cnes", sa.String(10), nullable=False),
        sa.Column("requester_name", sa.String(200), nullable=False),
        sa.Column("executor_cnes", sa.String(10), nullable=False),
        sa.Column("executor_name", sa.String(200), nullable=False),
        sa.Column("executor_address", sa.String(500), nullable=True),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["integration_system_id"],
            ["systems.id"],
            name="fk_integ_execmap_system",
            ondelete="RESTRICT",
        ),
    )

    op.create_index("idx_integ_execmap_system", "integration_execution_mappings", ["integration_system_id"])
    op.create_index(
        "idx_integ_execmap_cnes",
        "integration_execution_mappings",
        ["requester_cnes", "executor_cnes"],
    )

    # ══════════════════════════════════════════════════════════════════
    # SEED DATA
    # ══════════════════════════════════════════════════════════════════

    # ── Departments (28) ──────────────────────────────────────────────
    dept_table = sa.table(
        "integration_departments",
        sa.column("id", sa.Uuid()),
        sa.column("integration_system_id", sa.Uuid()),
        sa.column("department_name", sa.String),
        sa.column("cnes_code", sa.String),
        sa.column("group_id", sa.Uuid()),
        sa.column("department_type", sa.String),
        sa.column("is_remote", sa.Boolean),
    )

    departments_data = [
        ("AMBULATORIO VIRTUAL DO AMAZONAS", "197130", "f24835c2-ce80-40ed-aa06-72f399442074", "FULLINTEGRATION", True),
        ("CAIC AFRANIO SOARES", "2017210", "20b77e5a-ca2c-49b7-82ff-454015a4caa7", "FULLINTEGRATION", False),
        ("CAIC ALBERTO CARREIRA", "2011824", "3804e865-6fe3-4497-b035-b6ac40fd47fa", "FULLINTEGRATION", False),
        (
            "CAIC ANA MARIA DOS SANTOS PEREIRA BRAGA",
            "2018527",
            "feace9c8-1c7d-4b22-9b44-22afd5a35946",
            "FULLINTEGRATION",
            False,
        ),
        ("CAIC DRA JOSEPHINA DE MELLO", "2018519", "321b8ff9-8c79-46e9-9ec6-2cc4f062f740", "FULLINTEGRATION", False),
        (
            "CAIC DRA MARIA HELENA FREITAS DE GOES",
            "2016982",
            "d9281b2a-e00b-4e54-a836-e1ba0a13f911",
            "FULLINTEGRATION",
            False,
        ),
        ("CAIC DR JOSE CONTENTE", "2013738", "94a465f6-23b4-4825-b807-dd7646564b92", "FULLINTEGRATION", False),
        ("CAIC DR MOURA TAPAJOZ", "2013592", "ba7dcb93-90db-45aa-966d-009e94750461", "FULLINTEGRATION", False),
        ("CAIC JOSE CARLOS MESTRINHO", "2011840", "b502fe5f-bc55-418a-b5e1-568d463fe175", "FULLINTEGRATION", False),
        ("CAIMI ADA RODRIGUES VIANA", "3212270", "0b90e2fd-3747-441a-bcc2-426fec900768", "FULLINTEGRATION", False),
        ("CAIMI DR PAULO LIMA", "2012057", "a512c2c8-c840-4189-88bd-a06fad9947cf", "FULLINTEGRATION", False),
        (
            "CER II PROFESSOR ROLLS GRACIE FISICO E INTELECTUAL",
            "5889545",
            "0bb89aeb-28da-4df2-bd9f-e2843ba93bb0",
            "FULLINTEGRATION",
            False,
        ),
        (
            "COMPLEXO REGULADOR DO AMAZONAS",
            "5726832",
            "1def09cd-f850-4947-a1ee-aa59e1bf11c4",
            "PARTIALINTEGRATION",
            False,
        ),
        ("FUNDACAO DE MEDICINA TROPICAL", "2013606", "e73a0efa-1e0f-4859-bc20-485562c1299c", "FULLINTEGRATION", False),
        ("POLICLINICA CODAJAS", "2018756", "81028c06-7e44-48cc-aea0-4e44b38da61d", "FULLINTEGRATION", False),
        (
            "POLICLINICA DA POLICIA MILITAR TENENTE WEBER",
            "7778651",
            "f1536f16-267a-419d-9705-2b48df645b18",
            "FULLINTEGRATION",
            False,
        ),
        (
            "POLICLINICA JOAO DOS SANTOS BRAGA",
            "3500179",
            "6f250595-a5f6-40db-a53f-cd2a7890a519",
            "FULLINTEGRATION",
            False,
        ),
        ("POLICLINICA ZENO LANZINI", "3042626", "cfd44a8d-d4a6-40c5-a782-95c3e21ae312", "FULLINTEGRATION", False),
        ("SPA E POLICLINICA DR JOSE LINS", "5222710", "72edb1af-a4ef-4822-8528-f7c8aee4e863", "FULLINTEGRATION", False),
        ("USF AJURICABA", "2704951", "70ca1d2e-a372-4225-b263-5bc1a4a2bb1b", "FULLINTEGRATION", False),
        ("USF AUGIAS GADELHA", "2014750", "7fbc3922-5c76-490f-b04a-1eb76e2d76d3", "FULLINTEGRATION", False),
        ("USF DEODATO DE MIRANDA LEAO", "2013479", "c98b2697-65fb-4a7c-932e-aaacc8bae287", "FULLINTEGRATION", False),
        ("USF DR ALFREDO CAMPOS", "2013916", "58501e5e-72f6-4709-8fb2-3234990bb8c6", "FULLINTEGRATION", False),
        ("USF DR JOSE FIGLIUOLO", "7594372", "c46be4a1-8cd8-49bd-a840-6d1d5b034657", "FULLINTEGRATION", False),
        (
            "USF DR WALDIR BUGALHO DE MEDEIROS",
            "2013878",
            "aa03387c-4530-401c-a20e-c450e7559eb0",
            "FULLINTEGRATION",
            False,
        ),
        (
            "USF LUCIO FLAVIO DE VASCONCELOS DIAS",
            "2013002",
            "3d1a0309-a01c-4617-b1ac-5031f10bb69a",
            "FULLINTEGRATION",
            False,
        ),
        ("USF SANTA LUZIA", "2013517", "b4c57e7a-6e7b-4efa-bc9c-fc2774fb02ab", "FULLINTEGRATION", False),
        ("USF SAO VICENTE DE PAULO", "2014769", "6d4f4128-332a-4c9c-b93a-ccc001d917e6", "FULLINTEGRATION", False),
    ]

    op.bulk_insert(
        dept_table,
        [
            {
                "id": uuid.uuid4(),
                "integration_system_id": SAUDE_AM_DIGITAL_ID,
                "department_name": name,
                "cnes_code": cnes,
                "group_id": uuid.UUID(gid),
                "department_type": dtype,
                "is_remote": remote,
            }
            for name, cnes, gid, dtype, remote in departments_data
        ],
    )

    # ── Procedures (46) ───────────────────────────────────────────────
    proc_table = sa.table(
        "integration_procedures",
        sa.column("id", sa.Uuid()),
        sa.column("integration_system_id", sa.Uuid()),
        sa.column("procedure_name", sa.String),
        sa.column("specialty_name", sa.String),
        sa.column("specialty_id", sa.Integer),
        sa.column("work_scale_name", sa.String),
        sa.column("work_scale_id", sa.String),
    )

    procedures_data = [
        ("TELECONSULTA EM ALERGIA E IMUNOLOGIA GERAL", "Alergologia", 31, "Alergologia", "-O_AOmgx5BHsvhtMdOLU"),
        ("TELECONSULTA EM CARDIOLOGIA GERAL", "Cardiologia", 3, "Cardiologia", "-OK2-FBJ7ESOlQD88Jxh"),
        ("TELECONSULTA EM CARDIOLOGIA GERAL - RETORNO", "Cardiologia", 3, "Cardiologia", "-OK2-FBJ7ESOlQD88Jxh"),
        ("TELECONSULTA EM CARDIOLOGIA PEDIATRICA", "Cardiologia", 3, "Cardiologia", "-OK2-FBJ7ESOlQD88Jxh"),
        ("TELECONSULTA EM CARDIOLOGIA PEDIATRICA - RETORNO", "Cardiologia", 3, "Cardiologia", "-OK2-FBJ7ESOlQD88Jxh"),
        ("TELECONSULTA EM CARDIOLOGIA - RISCO CIRURGICO", "Cardiologia", 3, "Cardiologia", "-OK2-FBJ7ESOlQD88Jxh"),
        ("TELECONSULTA EM DERMATOLOGIA GERAL", "Dermatologia", 5, "Dermatologia", "-OK2-HkONyXIdb-tUZOO"),
        ("TELECONSULTA EM DERMATOLOGIA GERAL - RETORNO", "Dermatologia", 5, "Dermatologia", "-OK2-HkONyXIdb-tUZOO"),
        ("TELECONSULTA EM DERMATOLOGIA PEDIATRICA", "Dermatologia", 5, "Dermatologia", "-OK2-HkONyXIdb-tUZOO"),
        (
            "TELECONSULTA EM DERMATOLOGIA PEDIATRICA - RETORNO",
            "Dermatologia",
            5,
            "Dermatologia",
            "-OK2-HkONyXIdb-tUZOO",
        ),
        (
            "TELECONSULTA EM ENDOCRINOLOGIA E METABOLOGIA GERAL",
            "Endocrinologia",
            10,
            "Endocrinologia",
            "-OK2-NKnB8Fc6YEVdfd5",
        ),
        (
            "TELECONSULTA EM ENDOCRINOLOGIA E METABOLOGIA GERAL - RETORNO",
            "Endocrinologia",
            10,
            "Endocrinologia",
            "-OK2-NKnB8Fc6YEVdfd6",
        ),
        (
            "TELECONSULTA EM ENDOCRINOLOGIA E METABOLOGIA PEDIATRICA",
            "Endocrinologia",
            10,
            "Endocrinologia",
            "-OK2-NKnB8Fc6YEVdfd7",
        ),
        (
            "TELECONSULTA EM ENDOCRINOLOGIA E METABOLOGIA PEDIATRICA - RETORNO",
            "Endocrinologia",
            10,
            "Endocrinologia",
            "-OK2-NKnB8Fc6YEVdfd8",
        ),
        (
            "TELECONSULTA EM GASTROENTEROLOGIA GERAL",
            "Gastroenterologia",
            11,
            "Gastroenterologia",
            "-O_AObo79iXdtQ0BPWSX",
        ),
        ("TELECONSULTA EM GERIATRIA", "Geriatria", 29, "Geriatria", "-O_AOgr48SRnGC3xws29"),
        ("TELECONSULTA EM GINECOLOGIA - GERAL", "Ginecologia", 12, "Ginecologia", "-OK2-AohU8DV7inuPLMl"),
        ("TELECONSULTA EM GINECOLOGIA OBSTETRICIA", "Obstetr\u00edcia", 13, "Obstetr\u00edcia", "-OLkLfXb8HaOcxbo0lmY"),
        (
            "TELECONSULTA EM GINECOLOGIA OBSTETRICIA - RETORNO",
            "Obstetr\u00edcia",
            13,
            "Obstetr\u00edcia",
            "-OLkLfXb8HaOcxbo0lmY",
        ),
        ("TELECONSULTA EM GINECOLOGIA - RETORNO", "Ginecologia", 12, "Ginecologia", "-OK2-AohU8DV7inuPLMl"),
        ("TELECONSULTA EM NEUROLOGIA GERAL", "Neurologia", 16, "Neurologia", "-OK2-RM2L3QFk38f37SD"),
        ("TELECONSULTA EM NEUROLOGIA GERAL - RETORNO", "Neurologia", 16, "Neurologia", "-OK2-RM2L3QFk38f37SD"),
        (
            "TELECONSULTA EM NEUROLOGIA PEDIATRICA",
            "Neurologia Infantil",
            27,
            "Neurologia Infantil",
            "-OK2-mx_1IdQUkOz_hxz",
        ),
        (
            "TELECONSULTA EM NEUROLOGIA PEDIATRICA - RETORNO",
            "Neurologia Infantil",
            27,
            "Neurologia Infantil",
            "-OK2-mx_1IdQUkOz_hxz",
        ),
        ("TELECONSULTA EM NUTRICAO GERAL", "Nutricionista", 17, "Nutricionista", "-OK2-Z9tHG3V5qFo-m2N"),
        ("TELECONSULTA EM NUTRICAO GERAL \u2013 RETORNO", "Nutricionista", 17, "Nutricionista", "-OK2-Z9tHG3V5qFo-m2N"),
        ("TELECONSULTA EM NUTRICAO PEDIATRICA", "Nutricionista", 17, "Nutricionista", "-OK2-Z9tHG3V5qFo-m2N"),
        (
            "TELECONSULTA EM NUTRICAO PEDIATRICA \u2013 RETORNO",
            "Nutricionista",
            17,
            "Nutricionista",
            "-OK2-Z9tHG3V5qFo-m2N",
        ),
        ("TELECONSULTA EM ORTOPEDIA GERAL", "Ortopedia", 19, "Ortopedia", "-OK2-kJPFTkhTXKrgyNG"),
        ("TELECONSULTA EM ORTOPEDIA GERAL - RETORNO", "Ortopedia", 19, "Ortopedia", "-OK2-kJPFTkhTXKrgyNG"),
        ("TELECONSULTA EM ORTOPEDIA PEDIATRICA", "Ortopedia", 19, "Ortopedia", "-OK2-kJPFTkhTXKrgyNG"),
        ("TELECONSULTA EM ORTOPEDIA PEDIATRICA - RETORNO", "Ortopedia", 19, "Ortopedia", "-OK2-kJPFTkhTXKrgyNG"),
        ("TELECONSULTA EM PEDIATRIA", "Pediatria", 21, "Pediatria", "-OK2-UjdGPK2_y5g4yXa"),
        ("TELECONSULTA EM PEDIATRIA - RETORNO", "Pediatria", 21, "Pediatria", "-OK2-UjdGPK2_y5g4yXa"),
        ("TELECONSULTA EM PSICOLOGIA GERAL", "Psicologia", 7, "Psicologia", "-OK2-4IHLKmEkOKLjuzc"),
        ("TELECONSULTA EM PSICOLOGIA GERAL \u2013 RETORNO", "Psicologia", 7, "Psicologia", "-OK2-4IHLKmEkOKLjuzc"),
        ("TELECONSULTA EM PSICOLOGIA PEDIATRICA", "Psicologia", 7, "Psicologia", "-OK2-4IHLKmEkOKLjuzc"),
        ("TELECONSULTA EM PSICOLOGIA PEDIATRICA \u2013 RETORNO", "Psicologia", 7, "Psicologia", "-OK2-4IHLKmEkOKLjuzc"),
        ("TELECONSULTA EM PSIQUIATRIA GERAL", "Psiquiatria", 8, "Psiquiatria", "-OK1zvNbu40ZLooUKkaq"),
        ("TELECONSULTA EM PSIQUIATRIA GERAL - RETORNO", "Psiquiatria", 8, "Psiquiatria", "-OK1zvNbu40ZLooUKkaq"),
        (
            "TELECONSULTA EM PSIQUIATRIA PEDIATRICA",
            "Psiquiatria Infantil",
            22,
            "Psiquiatria Infantil",
            "-OLkLziS2lOlGfdEifBO",
        ),
        (
            "TELECONSULTA EM PSIQUIATRIA PEDIATRICA - RETORNO",
            "Psiquiatria Infantil",
            22,
            "Psiquiatria Infantil",
            "-OLkLziS2lOlGfdEifBO",
        ),
        ("TELECONSULTA EM UROLOGIA GERAL", "Urologia", 25, "Urologia", "-OK2-bqY9RQPkAZ1gq6D"),
        ("TELECONSULTA EM UROLOGIA GERAL - RETORNO", "Urologia", 25, "Urologia", "-OK2-bqY9RQPkAZ1gq6D"),
        ("TELECONSULTA EM UROLOGIA PEDIATRICA", "Urologia", 25, "Urologia", "-OK2-bqY9RQPkAZ1gq6D"),
        ("TELECONSULTA EM UROLOGIA PEDIATRICA - RETORNO", "Urologia", 25, "Urologia", "-OK2-bqY9RQPkAZ1gq6D"),
    ]

    op.bulk_insert(
        proc_table,
        [
            {
                "id": uuid.uuid4(),
                "integration_system_id": SAUDE_AM_DIGITAL_ID,
                "procedure_name": pname,
                "specialty_name": sname,
                "specialty_id": sid,
                "work_scale_name": wsname,
                "work_scale_id": wsid,
            }
            for pname, sname, sid, wsname, wsid in procedures_data
        ],
    )

    # ── Execution Mappings (1054 rows) ────────────────────────────────
    # NOTE: The 1054 execution mappings are loaded from CSV via the
    # seed script (src/regulahub/scripts/seed_execution_mappings.py).
    # They are NOT inlined in this migration due to volume.
    # The table structure above is sufficient; run the seed script
    # after migration to populate the data.

    # ══════════════════════════════════════════════════════════════════
    # ENDPOINT CORRECTIONS — SAUDE AM DIGITAL
    # ══════════════════════════════════════════════════════════════════

    # Delete the 6 placeholder endpoints from migration 001
    op.execute(
        sa.text(f"DELETE FROM system_endpoints WHERE system_id = '{SAUDE_AM_DIGITAL_ID}'::uuid")
    )

    # Insert the 7 correct endpoints
    endpoints_table = sa.table(
        "system_endpoints",
        sa.column("id", sa.Uuid()),
        sa.column("system_id", sa.Uuid()),
        sa.column("name", sa.String),
        sa.column("protocol", sa.String),
        sa.column("http_method", sa.String),
        sa.column("path", sa.String),
        sa.column("base_url_override", sa.String),
        sa.column("config", sa.JSON),
        sa.column("sort_order", sa.Integer),
    )

    endpoint_config = {"auth_type": "api_key", "headers": {"PTM-Client-Domain": "SAUDEAMDIGITAL"}}
    base_url = "https://api.sosportal.com.br/api"

    op.bulk_insert(
        endpoints_table,
        [
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "find_patient_by_cpf",
                "protocol": "REST",
                "http_method": "GET",
                "path": "/integration/patient/idbycpf",
                "base_url_override": f"{base_url}/core/v1",
                "config": endpoint_config,
                "sort_order": 0,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "register_patient",
                "protocol": "REST",
                "http_method": "POST",
                "path": "/integration/patient/register",
                "base_url_override": f"{base_url}/auth/v1",
                "config": endpoint_config,
                "sort_order": 1,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "update_patient",
                "protocol": "REST",
                "http_method": "PATCH",
                "path": "/integration/patient/{id}",
                "base_url_override": f"{base_url}/core/v1",
                "config": endpoint_config,
                "sort_order": 2,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "list_doctors",
                "protocol": "REST",
                "http_method": "GET",
                "path": "/integration/doctor",
                "base_url_override": f"{base_url}/core/v1",
                "config": endpoint_config,
                "sort_order": 3,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "check_appointment",
                "protocol": "REST",
                "http_method": "GET",
                "path": "/integration/appointment/external/{externalId}",
                "base_url_override": f"{base_url}/core/v1",
                "config": endpoint_config,
                "sort_order": 4,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "create_appointment",
                "protocol": "REST",
                "http_method": "POST",
                "path": "/integration/appointment",
                "base_url_override": f"{base_url}/core/v1",
                "config": endpoint_config,
                "sort_order": 5,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "cancel_appointment",
                "protocol": "REST",
                "http_method": "PUT",
                "path": "/integration/appointment/external/{externalId}",
                "base_url_override": f"{base_url}/core/v1",
                "config": endpoint_config,
                "sort_order": 6,
            },
        ],
    )


def downgrade() -> None:
    # ── Restore original Saude AM Digital endpoints ───────────────────
    # Delete the 7 corrected endpoints
    op.execute(
        sa.text(f"DELETE FROM system_endpoints WHERE system_id = '{SAUDE_AM_DIGITAL_ID}'::uuid")
    )

    # Re-insert the original 6 placeholder endpoints from migration 001
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
    )

    original_config_auth = {"auth_pattern": "api_key", "host_hint": "auth"}
    original_config = {"auth_pattern": "api_key"}

    op.bulk_insert(
        endpoints_table,
        [
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "register_patient",
                "protocol": "REST",
                "http_method": "POST",
                "path": "/api/patients",
                "config": original_config_auth,
                "sort_order": 0,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "find_patient",
                "protocol": "REST",
                "http_method": "GET",
                "path": "/api/patients",
                "config": original_config,
                "sort_order": 1,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "update_patient",
                "protocol": "REST",
                "http_method": "PUT",
                "path": "/api/patients/{id}",
                "config": original_config,
                "sort_order": 2,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "list_doctors",
                "protocol": "REST",
                "http_method": "GET",
                "path": "/api/doctors",
                "config": original_config,
                "sort_order": 3,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "find_reminder",
                "protocol": "REST",
                "http_method": "GET",
                "path": "/api/reminders",
                "config": original_config,
                "sort_order": 4,
            },
            {
                "id": uuid.uuid4(),
                "system_id": SAUDE_AM_DIGITAL_ID,
                "name": "create_reminder",
                "protocol": "REST",
                "http_method": "POST",
                "path": "/api/reminders",
                "config": original_config,
                "sort_order": 5,
            },
        ],
    )

    # ── Drop tables (reverse creation order) ──────────────────────────
    op.drop_index("idx_integ_execmap_cnes", table_name="integration_execution_mappings")
    op.drop_index("idx_integ_execmap_system", table_name="integration_execution_mappings")
    op.drop_table("integration_execution_mappings")

    op.drop_index("idx_integ_proc_system", table_name="integration_procedures")
    op.drop_table("integration_procedures")

    op.drop_index("idx_integ_dept_cnes", table_name="integration_departments")
    op.drop_index("idx_integ_dept_system", table_name="integration_departments")
    op.drop_table("integration_departments")
