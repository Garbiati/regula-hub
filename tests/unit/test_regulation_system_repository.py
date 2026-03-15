"""Tests for RegulationSystemRepository using in-memory SQLite."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from regulahub.db.models import Base, SystemType
from regulahub.db.repositories.regulation_system import RegulationSystemRepository

REG_TYPE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        session.add(SystemType(id=REG_TYPE_ID, code="regulation", name="Regulation"))
        session.add(SystemType(code="integration", name="Integration"))
        session.add(SystemType(code="platform", name="Platform"))
        await session.flush()
        yield session

    await engine.dispose()


@pytest.fixture
def repo(db_session):
    return RegulationSystemRepository(db_session)


async def _create_system(repo: RegulationSystemRepository, **overrides):
    defaults = {
        "code": "SISREG",
        "name": "SisReg",
        "description": "Sistema Nacional de Regulação",
        "base_url": "https://sisregiii.saude.gov.br",
        "route_segment": "sisreg",
        "icon": "Monitor",
        "table_prefix": "sisreg",
    }
    defaults.update(overrides)
    return await repo.create(defaults)


async def _create_profile(repo: RegulationSystemRepository, system_id: uuid.UUID, **overrides):
    defaults = {
        "scope": "regulation",
        "system_id": system_id,
        "profile_name": "VIDEOFONISTA",
        "description": "State-wide view",
        "sort_order": 0,
    }
    defaults.update(overrides)
    return await repo.create_profile(defaults)


# ── System CRUD ──────────────────────────────────────────────────────


async def test_create_and_get_by_id(repo, db_session):
    system = await _create_system(repo)
    await db_session.flush()
    found = await repo.get_by_id(system.id)
    assert found is not None
    assert found.code == "SISREG"
    assert found.name == "SisReg"


async def test_get_by_code(repo, db_session):
    await _create_system(repo)
    await db_session.flush()
    found = await repo.get_by_code("SISREG")
    assert found is not None
    assert found.name == "SisReg"


async def test_list_active(repo, db_session):
    await _create_system(repo, code="SISREG", name="SisReg", table_prefix="sisreg")
    await _create_system(repo, code="ESUS", name="e-SUS", table_prefix="esus")
    await db_session.flush()
    items = await repo.list_active()
    assert len(items) == 2
    codes = [s.code for s in items]
    assert "SISREG" in codes
    assert "ESUS" in codes


async def test_list_active_excludes_inactive(repo, db_session):
    system = await _create_system(repo)
    await db_session.flush()
    await repo.deactivate(system.id)
    await db_session.flush()
    items = await repo.list_active()
    assert len(items) == 0


async def test_update(repo, db_session):
    system = await _create_system(repo)
    await db_session.flush()
    updated = await repo.update(system.id, {"name": "SisReg III"})
    assert updated is not None
    assert updated.name == "SisReg III"


async def test_update_nonexistent(repo):
    result = await repo.update(uuid.uuid4(), {"name": "nope"})
    assert result is None


async def test_deactivate(repo, db_session):
    system = await _create_system(repo)
    await db_session.flush()
    result = await repo.deactivate(system.id)
    assert result is True
    assert system.is_active is False


async def test_deactivate_nonexistent(repo):
    result = await repo.deactivate(uuid.uuid4())
    assert result is False


async def test_validate_system_code(repo, db_session):
    await _create_system(repo)
    await db_session.flush()
    assert await repo.validate_system_code("SISREG") is True
    assert await repo.validate_system_code("NONEXISTENT") is False


# ── Profile CRUD ─────────────────────────────────────────────────────


async def test_create_profile_and_list(repo, db_session):
    system = await _create_system(repo)
    await db_session.flush()
    await _create_profile(repo, system.id, profile_name="VIDEOFONISTA", sort_order=0)
    await _create_profile(repo, system.id, profile_name="SOLICITANTE", sort_order=1)
    await db_session.flush()

    profiles = await repo.get_profiles_for_system("SISREG")
    assert len(profiles) == 2
    assert profiles[0].profile_name == "VIDEOFONISTA"
    assert profiles[1].profile_name == "SOLICITANTE"


async def test_update_profile(repo, db_session):
    system = await _create_system(repo)
    await db_session.flush()
    profile = await _create_profile(repo, system.id)
    await db_session.flush()

    updated = await repo.update_profile(profile.id, {"description": "Updated description"})
    assert updated is not None
    assert updated.description == "Updated description"


async def test_update_profile_nonexistent(repo):
    result = await repo.update_profile(uuid.uuid4(), {"description": "nope"})
    assert result is None


async def test_delete_profile(repo, db_session):
    system = await _create_system(repo)
    await db_session.flush()
    profile = await _create_profile(repo, system.id)
    await db_session.flush()

    result = await repo.delete_profile(profile.id)
    assert result is True

    profiles = await repo.get_profiles_for_system("SISREG")
    assert len(profiles) == 0


async def test_delete_profile_nonexistent(repo):
    result = await repo.delete_profile(uuid.uuid4())
    assert result is False


async def test_profiles_empty_for_unknown_system(repo, db_session):
    profiles = await repo.get_profiles_for_system("UNKNOWN")
    assert len(profiles) == 0


async def test_resolve_profile_id(repo, db_session):
    system = await _create_system(repo)
    await db_session.flush()
    profile = await _create_profile(repo, system.id, profile_name="VIDEOFONISTA")
    await db_session.flush()

    resolved = await repo.resolve_profile_id("SISREG", "VIDEOFONISTA")
    assert resolved == profile.id

    not_found = await repo.resolve_profile_id("SISREG", "NONEXISTENT")
    assert not_found is None
