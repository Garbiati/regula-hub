"""Repository for users and user_selections tables."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.models import RegulaHubUser, RegulaHubUserSelection


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Users ──────────────────────────────────────────────────────────

    async def list_active(self) -> list[RegulaHubUser]:
        stmt = select(RegulaHubUser).where(RegulaHubUser.is_active.is_(True)).order_by(RegulaHubUser.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, user_id: uuid.UUID) -> RegulaHubUser | None:
        stmt = select(RegulaHubUser).where(RegulaHubUser.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Selections ─────────────────────────────────────────────────────

    async def get_selections_for_user(self, user_id: uuid.UUID) -> list[RegulaHubUserSelection]:
        stmt = (
            select(RegulaHubUserSelection)
            .where(RegulaHubUserSelection.user_id == user_id)
            .order_by(RegulaHubUserSelection.system, RegulaHubUserSelection.profile_type)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_selection(
        self,
        user_id: uuid.UUID,
        system: str,
        profile_type: str,
        state: str,
        state_name: str,
        selected_users: list[str],
    ) -> RegulaHubUserSelection:
        stmt = (
            select(RegulaHubUserSelection)
            .where(RegulaHubUserSelection.user_id == user_id)
            .where(RegulaHubUserSelection.system == system)
            .where(RegulaHubUserSelection.profile_type == profile_type)
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.state = state
            existing.state_name = state_name
            existing.selected_users = selected_users
            existing.updated_at = datetime.now(UTC)
            await self._session.flush()
            return existing

        selection = RegulaHubUserSelection(
            user_id=user_id,
            system=system,
            profile_type=profile_type,
            state=state,
            state_name=state_name,
            selected_users=selected_users,
        )
        self._session.add(selection)
        await self._session.flush()
        return selection

    async def delete_selection(self, user_id: uuid.UUID, system: str, profile_type: str) -> bool:
        stmt = (
            select(RegulaHubUserSelection)
            .where(RegulaHubUserSelection.user_id == user_id)
            .where(RegulaHubUserSelection.system == system)
            .where(RegulaHubUserSelection.profile_type == profile_type)
        )
        result = await self._session.execute(stmt)
        selection = result.scalar_one_or_none()
        if not selection:
            return False
        await self._session.delete(selection)
        await self._session.flush()
        return True
