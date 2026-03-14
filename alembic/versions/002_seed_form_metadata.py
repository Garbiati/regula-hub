"""seed form_metadata into SisReg search_appointments endpoint config

Revision ID: 002
Revises: 001
Create Date: 2026-03-16

Data-only migration: merges form_metadata JSON into the existing config JSONB
of the search_appointments endpoint for SisReg.  No schema changes.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SISREG_CODE = "SISREG"
ENDPOINT_NAME = "search_appointments"

FORM_METADATA = {
    "version": 1,
    "updated_at": "2026-03-16T00:00:00Z",
    "search_types": [
        {"value": "solicitacao", "label_key": "consulta.type_solicitacao", "canonical_label": "Solicitação"},
        {"value": "agendamento", "label_key": "consulta.type_agendamento", "canonical_label": "Agendamento"},
        {"value": "execucao", "label_key": "consulta.type_execucao", "canonical_label": "Execução"},
        {"value": "confirmacao", "label_key": "consulta.type_confirmacao", "canonical_label": "Confirmação"},
        {"value": "cancelamento", "label_key": "consulta.type_cancelamento", "canonical_label": "Cancelamento"},
    ],
    "situations": [
        {
            "value": "1",
            "label_key": "consulta.sit_sol_pending_regulation",
            "canonical_label": "Solicitação / Pendente / Regulação",
            "applies_to": ["solicitacao"],
        },
        {
            "value": "2",
            "label_key": "consulta.sit_sol_pending_queue",
            "canonical_label": "Solicitação / Pendente / Fila de Espera",
            "applies_to": ["solicitacao"],
        },
        {
            "value": "3",
            "label_key": "consulta.sit_sol_cancelled",
            "canonical_label": "Solicitação / Cancelada",
            "applies_to": ["solicitacao", "cancelamento"],
        },
        {
            "value": "4",
            "label_key": "consulta.sit_sol_returned",
            "canonical_label": "Solicitação / Devolvida",
            "applies_to": ["solicitacao"],
        },
        {
            "value": "5",
            "label_key": "consulta.sit_sol_resent",
            "canonical_label": "Solicitação / Reenviada",
            "applies_to": ["solicitacao"],
        },
        {
            "value": "6",
            "label_key": "consulta.sit_sol_denied",
            "canonical_label": "Solicitação / Negada",
            "applies_to": ["solicitacao"],
        },
        {
            "value": "7",
            "label_key": "consulta.sit_sol_scheduled",
            "canonical_label": "Solicitação / Agendada",
            "applies_to": ["solicitacao", "agendamento", "execucao"],
        },
        {
            "value": "9",
            "label_key": "consulta.sit_sol_scheduled_queue",
            "canonical_label": "Solicitação / Agendada / Fila de Espera",
            "applies_to": ["solicitacao", "agendamento", "execucao"],
        },
        {
            "value": "10",
            "label_key": "consulta.sit_sched_cancelled",
            "canonical_label": "Agendamento / Cancelado",
            "applies_to": ["solicitacao", "agendamento", "execucao", "cancelamento"],
        },
        {
            "value": "11",
            "label_key": "consulta.sit_sched_confirmed",
            "canonical_label": "Agendamento / Confirmado",
            "applies_to": ["solicitacao", "agendamento", "execucao", "confirmacao"],
        },
        {
            "value": "12",
            "label_key": "consulta.sit_sched_absent",
            "canonical_label": "Agendamento / Falta",
            "applies_to": ["solicitacao", "agendamento", "execucao"],
        },
    ],
    "items_per_page": [
        {"value": "10", "label": "10"},
        {"value": "20", "label": "20"},
        {"value": "50", "label": "50"},
        {"value": "100", "label": "100"},
        {"value": "0", "label_key": "consulta.items_all", "canonical_label": "TODOS"},
    ],
    "defaults": {
        "search_type": "agendamento",
        "situation": "7",
        "items_per_page": "20",
    },
}


def upgrade() -> None:
    conn = op.get_bind()

    # Get the current config for the search_appointments endpoint
    row = conn.execute(
        sa.text(
            "SELECT se.id, se.config FROM system_endpoints se "
            "JOIN systems s ON se.system_id = s.id "
            "WHERE s.code = :sys_code AND se.name = :ep_name"
        ),
        {"sys_code": SISREG_CODE, "ep_name": ENDPOINT_NAME},
    ).fetchone()

    if row is None:
        return  # endpoint not seeded yet — skip silently

    endpoint_id, current_config = row[0], row[1]
    config = dict(current_config) if current_config else {}
    config["form_metadata"] = FORM_METADATA

    conn.execute(
        sa.text("UPDATE system_endpoints SET config = :config, updated_at = NOW() WHERE id = :id"),
        {"config": json.dumps(config), "id": str(endpoint_id)},
    )


def downgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(
        sa.text(
            "SELECT se.id, se.config FROM system_endpoints se "
            "JOIN systems s ON se.system_id = s.id "
            "WHERE s.code = :sys_code AND se.name = :ep_name"
        ),
        {"sys_code": SISREG_CODE, "ep_name": ENDPOINT_NAME},
    ).fetchone()

    if row is None:
        return

    endpoint_id, current_config = row[0], row[1]
    config = dict(current_config) if current_config else {}
    config.pop("form_metadata", None)

    conn.execute(
        sa.text("UPDATE system_endpoints SET config = :config, updated_at = NOW() WHERE id = :id"),
        {"config": json.dumps(config), "id": str(endpoint_id)},
    )
