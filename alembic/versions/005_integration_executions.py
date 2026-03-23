"""integration executions table for worker history tracking

Revision ID: 005
Revises: 004
Create Date: 2026-03-22

Creates the integration_executions table for tracking worker execution
history. Stores status, progress, and results of integration pushes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("integration_system_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("total_fetched", sa.Integer(), nullable=True),
        sa.Column("total_enriched", sa.Integer(), nullable=True),
        sa.Column("total_pushed", sa.Integer(), nullable=True),
        sa.Column("total_failed", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "progress_data",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by", sa.String(50), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["integration_system_id"],
            ["systems.id"],
            name="fk_integ_exec_system",
            ondelete="RESTRICT",
        ),
    )

    op.create_index("idx_integ_exec_system", "integration_executions", ["integration_system_id"])
    op.create_index("idx_integ_exec_status", "integration_executions", ["status"])
    op.create_index("idx_integ_exec_created", "integration_executions", ["created_at"], postgresql_using="btree")


def downgrade() -> None:
    op.drop_index("idx_integ_exec_created", table_name="integration_executions")
    op.drop_index("idx_integ_exec_status", table_name="integration_executions")
    op.drop_index("idx_integ_exec_system", table_name="integration_executions")
    op.drop_table("integration_executions")
