"""cadsus enrichment cache table for avoiding redundant CADSUS lookups

Revision ID: 004
Revises: 003
Create Date: 2026-03-20

Creates the cadsus_enrichment_cache table. One row per CNS, with a TTL-based
freshness check (enriched_at). The /enrich endpoint queries this cache before
calling CADSUS, skipping CNS enriched within the last 30 days.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cadsus_enrichment_cache",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cns", sa.String(20), nullable=False),
        sa.Column("cpf", sa.String(14), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("father_name", sa.String(200), nullable=True),
        sa.Column("race", sa.String(50), nullable=True),
        sa.Column("cns_definitivo", sa.String(20), nullable=True),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column(
            "enriched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
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
        sa.UniqueConstraint("cns", name="uq_enrich_cache_cns"),
    )

    op.create_index("idx_enrich_cache_enriched_at", "cadsus_enrichment_cache", ["enriched_at"])


def downgrade() -> None:
    op.drop_index("idx_enrich_cache_enriched_at", table_name="cadsus_enrichment_cache")
    op.drop_table("cadsus_enrichment_cache")
