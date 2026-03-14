"""SQLAlchemy declarative models for application tables.

Uses dialect-agnostic types (JSON, Uuid) so models work with both PostgreSQL
(production) and SQLite (tests). The Alembic migration uses PostgreSQL-specific
types (JSONB, UUID) for optimal production performance.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class SystemType(Base):
    """Reference table for system types (regulation, integration, platform)."""

    __tablename__ = "system_types"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class RegulaHubUser(Base):
    """Platform user (operator or administrator) — independent of external system credentials."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    login: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    cpf: Mapped[str | None] = mapped_column(String(14), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class System(Base):
    """Unified system — regulation or integration."""

    __tablename__ = "systems"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    system_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("system_types.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Regulation-specific
    route_segment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    table_prefix: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    # Integration-specific
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    state_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Common
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class RegulaHubUserSelection(Base):
    """Per-user, per-(system, profile) selection of operators/units."""

    __tablename__ = "user_selections"
    __table_args__ = (
        UniqueConstraint("user_id", "system", "profile_type", name="uq_sel_user_sys_prof"),
        Index("idx_sel_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    system: Mapped[str] = mapped_column(String(20), nullable=False)
    profile_type: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    state_name: Mapped[str] = mapped_column(String(50), nullable=False)
    selected_users: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class SystemProfile(Base):
    """Unified profile — regulation, integration, or platform scope."""

    __tablename__ = "system_profiles"
    __table_args__ = (Index("idx_sysprof_system", "system_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scope_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("system_types.id", ondelete="RESTRICT"), nullable=False
    )
    system_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("systems.id", ondelete="RESTRICT"), nullable=True
    )
    profile_name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class SystemEndpoint(Base):
    """Endpoint configuration for any system (regulation or integration)."""

    __tablename__ = "system_endpoints"
    __table_args__ = (
        UniqueConstraint("system_id", "name", name="uq_sysep_system_name"),
        Index("idx_sysep_system", "system_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    system_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("systems.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    protocol: Mapped[str] = mapped_column(String(10), nullable=False)
    http_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    base_url_override: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class UserProfile(Base):
    """Junction: user assigned to a system profile."""

    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "profile_id", name="uq_usrprof_user_profile"),
        Index("idx_usrprof_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("system_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class CachedScheduleExport(Base):
    """Persistent cache for SisReg schedule export rows — offline access when SisReg is unavailable."""

    __tablename__ = "sisreg_cached_exports"
    __table_args__ = (
        Index("idx_cached_exp_date_iso", "data_agendamento_iso"),
        Index("idx_cached_exp_procedure", "descricao_procedimento"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    solicitacao: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    data_agendamento: Mapped[str] = mapped_column(String(10), nullable=False)
    data_agendamento_iso: Mapped[date | None] = mapped_column(Date, nullable=True)
    descricao_procedimento: Mapped[str] = mapped_column(String(300), nullable=False)
    row_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class CachedEnrichment(Base):
    """CADSUS enrichment cache — one entry per CNS, TTL-based freshness."""

    __tablename__ = "cadsus_enrichment_cache"
    __table_args__ = (Index("idx_enrich_cache_enriched_at", "enriched_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cns: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(14), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    father_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    race: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cns_definitivo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    enriched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class Credential(Base):
    """Encrypted credential for external system access — per-user, per-profile."""

    __tablename__ = "credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "profile_id", "username", name="uq_cred_user_profile_username"),
        Index("idx_cred_user", "user_id"),
        Index("idx_cred_profile", "profile_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("system_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    state_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unit_cnes: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
