"""Repository for credentials table."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.models import Credential, System, SystemProfile


class CredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_system_and_profile(self, system: str, profile_type: str) -> list[Credential]:
        stmt = (
            select(Credential)
            .join(SystemProfile, Credential.profile_id == SystemProfile.id)
            .join(System, SystemProfile.system_id == System.id)
            .where(System.code == system)
            .where(func.upper(SystemProfile.profile_name) == profile_type.upper())
            .where(Credential.is_active.is_(True))
            .order_by(Credential.username)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_by_system(self, system: str) -> list[Credential]:
        stmt = (
            select(Credential)
            .join(SystemProfile, Credential.profile_id == SystemProfile.id)
            .join(System, SystemProfile.system_id == System.id)
            .where(System.code == system)
            .where(Credential.is_active.is_(True))
            .order_by(SystemProfile.profile_name, Credential.username)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_by_user_and_system(self, user_id: uuid.UUID, system: str) -> list[Credential]:
        stmt = (
            select(Credential)
            .join(SystemProfile, Credential.profile_id == SystemProfile.id)
            .join(System, SystemProfile.system_id == System.id)
            .where(Credential.user_id == user_id)
            .where(System.code == system)
            .where(Credential.is_active.is_(True))
            .order_by(SystemProfile.profile_name, Credential.username)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, credential_id: uuid.UUID) -> Credential | None:
        stmt = select(Credential).where(Credential.id == credential_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username_profile_system(self, username: str, profile_type: str, system: str) -> Credential | None:
        stmt = (
            select(Credential)
            .join(SystemProfile, Credential.profile_id == SystemProfile.id)
            .join(System, SystemProfile.system_id == System.id)
            .where(Credential.username == username)
            .where(func.upper(SystemProfile.profile_name) == profile_type.upper())
            .where(System.code == system)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_profile_username(
        self, user_id: uuid.UUID, profile_id: uuid.UUID, username: str
    ) -> Credential | None:
        stmt = (
            select(Credential)
            .where(Credential.user_id == user_id)
            .where(Credential.profile_id == profile_id)
            .where(Credential.username == username)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_distinct_states(self, system: str) -> list[tuple[str, str]]:
        stmt = (
            select(distinct(Credential.state), Credential.state_name)
            .join(SystemProfile, Credential.profile_id == SystemProfile.id)
            .join(System, SystemProfile.system_id == System.id)
            .where(System.code == system)
            .where(Credential.is_active.is_(True))
            .where(Credential.state.isnot(None))
            .order_by(Credential.state)
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_distinct_profiles(self, system: str) -> list[str]:
        stmt = (
            select(distinct(SystemProfile.profile_name))
            .join(Credential, Credential.profile_id == SystemProfile.id)
            .join(System, SystemProfile.system_id == System.id)
            .where(System.code == system)
            .where(Credential.is_active.is_(True))
            .order_by(SystemProfile.profile_name)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def create(self, data: dict) -> Credential:
        credential = Credential(**data)
        self._session.add(credential)
        await self._session.flush()
        return credential

    async def update(self, credential_id: uuid.UUID, data: dict) -> Credential | None:
        credential = await self.get_by_id(credential_id)
        if not credential:
            return None
        for key, value in data.items():
            if key not in ("id", "created_at") and hasattr(credential, key):
                setattr(credential, key, value)
        credential.updated_at = datetime.now(UTC)
        await self._session.flush()
        return credential

    async def deactivate(self, credential_id: uuid.UUID) -> bool:
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False
        credential.is_active = False
        credential.updated_at = datetime.now(UTC)
        await self._session.flush()
        return True
