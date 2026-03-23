"""integration appointments table for tracking appointment push records

Revision ID: 008
Revises: 007
Create Date: 2026-03-23

Creates the integration_appointments table for storing individual appointment
records pushed to integration systems. Links to integration_executions for
batch tracking and supports status/error tracking per appointment.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: str = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_appointments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("integration_system_id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=True),
        # Regulation identifiers
        sa.Column("regulation_code", sa.String(30), nullable=False),
        sa.Column("confirmation_key", sa.String(100), nullable=True),
        sa.Column("external_id", sa.String(200), nullable=True),
        # Patient data
        sa.Column("patient_name", sa.String(300), nullable=False),
        sa.Column("patient_cpf", sa.String(14), nullable=True),
        sa.Column("patient_cns", sa.String(20), nullable=True),
        sa.Column("patient_birth_date", sa.String(10), nullable=True),
        sa.Column("patient_phone", sa.String(20), nullable=True),
        sa.Column("patient_mother_name", sa.String(300), nullable=True),
        # Appointment data
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("appointment_time", sa.Time(), nullable=True),
        sa.Column("procedure_name", sa.String(300), nullable=False),
        sa.Column("department_executor", sa.String(200), nullable=True),
        sa.Column("department_executor_cnes", sa.String(10), nullable=True),
        sa.Column("department_solicitor", sa.String(200), nullable=True),
        sa.Column("department_solicitor_cnes", sa.String(10), nullable=True),
        sa.Column("doctor_name", sa.String(200), nullable=True),
        sa.Column("doctor_cpf", sa.String(14), nullable=True),
        # Status tracking
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_category", sa.String(50), nullable=True),
        # Integration metadata
        sa.Column(
            "integration_data",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "source_data",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Reference and lifecycle
        sa.Column("reference_date", sa.Date(), nullable=False),
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
            name="fk_intappt_system",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["integration_executions.id"],
            name="fk_intappt_execution",
            ondelete="SET NULL",
        ),
    )

    op.create_index("idx_intappt_system", "integration_appointments", ["integration_system_id"])
    op.create_index("idx_intappt_execution", "integration_appointments", ["execution_id"])
    op.create_index("idx_intappt_regulation_code", "integration_appointments", ["regulation_code"])
    op.create_index(
        "idx_intappt_external_id",
        "integration_appointments",
        ["external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_index("idx_intappt_status", "integration_appointments", ["status"])
    op.create_index("idx_intappt_date", "integration_appointments", ["appointment_date"])
    op.create_index("idx_intappt_reference_date", "integration_appointments", ["reference_date"])


def downgrade() -> None:
    op.drop_index("idx_intappt_reference_date", table_name="integration_appointments")
    op.drop_index("idx_intappt_date", table_name="integration_appointments")
    op.drop_index("idx_intappt_status", table_name="integration_appointments")
    op.drop_index(
        "idx_intappt_external_id",
        table_name="integration_appointments",
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.drop_index("idx_intappt_regulation_code", table_name="integration_appointments")
    op.drop_index("idx_intappt_execution", table_name="integration_appointments")
    op.drop_index("idx_intappt_system", table_name="integration_appointments")
    op.drop_table("integration_appointments")
