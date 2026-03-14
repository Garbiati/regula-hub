"""Repository for systems and system_profiles tables."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.models import System, SystemEndpoint, SystemProfile, SystemType


class RegulationSystemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Systems ──────────────────────────────────────────────────

    async def list_active(self) -> list[System]:
        stmt = (
            select(System)
            .join(SystemType, System.system_type_id == SystemType.id)
            .where(SystemType.code == "regulation")
            .where(System.is_active.is_(True))
            .order_by(System.code)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> System | None:
        stmt = select(System).where(System.code == code)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, system_id: uuid.UUID) -> System | None:
        stmt = select(System).where(System.id == system_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> System:
        # Resolve system_type_id from code if not provided
        if "system_type_id" not in data:
            type_code = data.pop("system_type", "regulation")
            stmt = select(SystemType.id).where(SystemType.code == type_code)
            result = await self._session.execute(stmt)
            type_id = result.scalar_one_or_none()
            if type_id:
                data["system_type_id"] = type_id
        system = System(**data)
        self._session.add(system)
        await self._session.flush()
        return system

    async def update(self, system_id: uuid.UUID, data: dict) -> System | None:
        system = await self.get_by_id(system_id)
        if not system:
            return None
        for key, value in data.items():
            if key not in ("id", "created_at") and hasattr(system, key):
                setattr(system, key, value)
        system.updated_at = datetime.now(UTC)
        await self._session.flush()
        return system

    async def deactivate(self, system_id: uuid.UUID) -> bool:
        system = await self.get_by_id(system_id)
        if not system:
            return False
        system.is_active = False
        system.updated_at = datetime.now(UTC)
        await self._session.flush()
        return True

    async def validate_system_code(self, code: str) -> bool:
        system = await self.get_by_code(code)
        return system is not None and system.is_active

    # ── Profiles ─────────────────────────────────────────────────

    async def get_profiles_for_system(self, system_code: str) -> list[SystemProfile]:
        stmt = (
            select(SystemProfile)
            .join(System, SystemProfile.system_id == System.id)
            .where(System.code == system_code)
            .where(SystemProfile.is_active.is_(True))
            .order_by(SystemProfile.sort_order)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_system_profile_by_id(self, profile_id: uuid.UUID) -> SystemProfile | None:
        stmt = select(SystemProfile).where(SystemProfile.id == profile_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_profile(self, data: dict) -> SystemProfile:
        # Resolve scope_id from scope code if not provided
        if "scope_id" not in data:
            scope_code = data.pop("scope", "regulation")
            stmt = select(SystemType.id).where(SystemType.code == scope_code)
            result = await self._session.execute(stmt)
            scope_id = result.scalar_one_or_none()
            if scope_id:
                data["scope_id"] = scope_id
        profile = SystemProfile(**data)
        self._session.add(profile)
        await self._session.flush()
        return profile

    async def update_profile(self, profile_id: uuid.UUID, data: dict) -> SystemProfile | None:
        stmt = select(SystemProfile).where(SystemProfile.id == profile_id)
        result = await self._session.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            return None
        for key, value in data.items():
            if key not in ("id", "created_at") and hasattr(profile, key):
                setattr(profile, key, value)
        profile.updated_at = datetime.now(UTC)
        await self._session.flush()
        return profile

    async def delete_profile(self, profile_id: uuid.UUID) -> bool:
        stmt = select(SystemProfile).where(SystemProfile.id == profile_id)
        result = await self._session.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            return False
        await self._session.delete(profile)
        await self._session.flush()
        return True

    async def resolve_profile_id(self, system_code: str, profile_name: str) -> uuid.UUID | None:
        """Resolve a profile UUID from system code + profile name."""
        stmt = (
            select(SystemProfile.id)
            .join(System, SystemProfile.system_id == System.id)
            .where(System.code == system_code)
            .where(SystemProfile.profile_name == profile_name.upper())
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Endpoints ──────────────────────────────────────────────────

    async def get_endpoint_by_system_and_name(self, system_code: str, endpoint_name: str) -> SystemEndpoint | None:
        """Fetch a single endpoint by system code + endpoint name."""
        stmt = (
            select(SystemEndpoint)
            .join(System, SystemEndpoint.system_id == System.id)
            .where(System.code == system_code)
            .where(SystemEndpoint.name == endpoint_name)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_endpoint_config(self, endpoint_id: uuid.UUID, config: dict) -> SystemEndpoint | None:
        """Replace the entire config JSONB for an endpoint."""
        stmt = select(SystemEndpoint).where(SystemEndpoint.id == endpoint_id)
        result = await self._session.execute(stmt)
        endpoint = result.scalar_one_or_none()
        if not endpoint:
            return None
        endpoint.config = config
        endpoint.updated_at = datetime.now(UTC)
        await self._session.flush()
        return endpoint
