"""cached schedule exports table for offline SisReg access

Revision ID: 003
Revises: 002
Create Date: 2026-03-20

Creates the sisreg_cached_exports table for persistent caching of
schedule export rows. Enables offline access when SisReg is unavailable
(blocked between 8h-15h).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sisreg_cached_exports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("solicitacao", sa.String(30), nullable=False),
        sa.Column("data_agendamento", sa.String(10), nullable=False),
        sa.Column("data_agendamento_iso", sa.Date(), nullable=True),
        sa.Column("descricao_procedimento", sa.String(300), nullable=False),
        sa.Column(
            "row_data",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("solicitacao", name="uq_cached_exp_solicitacao"),
    )

    op.create_index("idx_cached_exp_date_iso", "sisreg_cached_exports", ["data_agendamento_iso"])
    op.create_index("idx_cached_exp_procedure", "sisreg_cached_exports", ["descricao_procedimento"])


def downgrade() -> None:
    op.drop_index("idx_cached_exp_procedure", table_name="sisreg_cached_exports")
    op.drop_index("idx_cached_exp_date_iso", table_name="sisreg_cached_exports")
    op.drop_table("sisreg_cached_exports")
