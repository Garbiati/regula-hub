"""Tests for CredentialRepository using in-memory SQLite."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from regulahub.db.models import Base, Credential, System, SystemProfile, SystemType
from regulahub.db.repositories.credential import CredentialRepository

# Fixed IDs for test seed data
REG_TYPE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SISREG_ID = uuid.uuid4()
VF_PROFILE_ID = uuid.uuid4()
SOL_PROFILE_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # Seed system type + regulation system + profiles
        session.add(SystemType(id=REG_TYPE_ID, code="regulation", name="Regulation"))
        session.add(
            System(id=SISREG_ID, system_type_id=REG_TYPE_ID, code="SISREG", name="SisReg", table_prefix="sisreg")
        )
        session.add(
            SystemProfile(
                id=VF_PROFILE_ID,
                scope_id=REG_TYPE_ID,
                system_id=SISREG_ID,
                profile_name="VIDEOFONISTA",
                description="State-wide view",
            )
        )
        session.add(
            SystemProfile(
                id=SOL_PROFILE_ID,
                scope_id=REG_TYPE_ID,
                system_id=SISREG_ID,
                profile_name="SOLICITANTE",
                description="Unit-scoped view",
            )
        )
        await session.flush()
        yield session

    await engine.dispose()


@pytest.fixture
def repo(db_session):
    return CredentialRepository(db_session)


async def _create_sample(repo: CredentialRepository, **overrides) -> Credential:
    defaults = {
        "user_id": USER_ID,
        "profile_id": VF_PROFILE_ID,
        "username": "user1",
        "encrypted_password": "encrypted_token",
    }
    defaults.update(overrides)
    return await repo.create(defaults)


async def test_create_and_get_by_id(repo, db_session):
    cred = await _create_sample(repo)
    await db_session.flush()
    found = await repo.get_by_id(cred.id)
    assert found is not None
    assert found.username == "user1"


async def test_get_active_by_system_and_profile(repo, db_session):
    await _create_sample(repo, username="vf1", profile_id=VF_PROFILE_ID)
    await _create_sample(repo, username="op1", profile_id=SOL_PROFILE_ID)
    await db_session.flush()

    vfs = await repo.get_active_by_system_and_profile("SISREG", "videofonista")
    assert len(vfs) == 1
    assert vfs[0].username == "vf1"


async def test_get_active_by_system(repo, db_session):
    await _create_sample(repo, username="vf1", profile_id=VF_PROFILE_ID)
    await _create_sample(repo, username="op1", profile_id=SOL_PROFILE_ID)
    await db_session.flush()

    all_creds = await repo.get_active_by_system("SISREG")
    assert len(all_creds) == 2


async def test_get_by_username_profile_system(repo, db_session):
    await _create_sample(repo, username="vf1")
    await db_session.flush()

    found = await repo.get_by_username_profile_system("vf1", "videofonista", "SISREG")
    assert found is not None
    assert found.username == "vf1"

    not_found = await repo.get_by_username_profile_system("vf1", "solicitante", "SISREG")
    assert not_found is None


async def test_get_by_user_profile_username(repo, db_session):
    await _create_sample(repo, username="vf1")
    await db_session.flush()

    found = await repo.get_by_user_profile_username(USER_ID, VF_PROFILE_ID, "vf1")
    assert found is not None

    not_found = await repo.get_by_user_profile_username(USER_ID, SOL_PROFILE_ID, "vf1")
    assert not_found is None


async def test_get_distinct_states(repo, db_session):
    await _create_sample(repo, username="u1", state="AM", state_name="Amazonas")
    await _create_sample(repo, username="u2", state="SP", state_name="São Paulo")
    await db_session.flush()

    states = await repo.get_distinct_states("SISREG")
    state_codes = [s for s, _ in states]
    assert "AM" in state_codes
    assert "SP" in state_codes


async def test_get_distinct_profiles(repo, db_session):
    await _create_sample(repo, username="vf1", profile_id=VF_PROFILE_ID)
    await _create_sample(repo, username="op1", profile_id=SOL_PROFILE_ID)
    await db_session.flush()

    profiles = await repo.get_distinct_profiles("SISREG")
    assert "VIDEOFONISTA" in profiles
    assert "SOLICITANTE" in profiles


async def test_update(repo, db_session):
    cred = await _create_sample(repo)
    await db_session.flush()

    updated = await repo.update(cred.id, {"state": "SP", "state_name": "São Paulo"})
    assert updated is not None
    assert updated.state == "SP"


async def test_deactivate(repo, db_session):
    cred = await _create_sample(repo)
    await db_session.flush()

    result = await repo.deactivate(cred.id)
    assert result is True
    assert cred.is_active is False

    active = await repo.get_active_by_system("SISREG")
    assert len(active) == 0


async def test_deactivate_nonexistent(repo):
    result = await repo.deactivate(uuid.uuid4())
    assert result is False
