"""Tests for IntegrationExecutionRepository using in-memory SQLite."""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from regulahub.db.models import Base, System, SystemType
from regulahub.db.repositories.integration_execution import IntegrationExecutionRepository

INTEGRATION_TYPE_ID = uuid.uuid4()
TEST_SYSTEM_ID = uuid.uuid4()


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # Seed system type and system
        session.add(SystemType(id=INTEGRATION_TYPE_ID, code="integration", name="Integration"))
        session.add(
            System(
                id=TEST_SYSTEM_ID,
                system_type_id=INTEGRATION_TYPE_ID,
                code="TEST_SYSTEM",
                name="Test Integration System",
            )
        )
        await session.flush()
        yield session

    await engine.dispose()


@pytest.fixture
def repo(db_session):
    return IntegrationExecutionRepository(db_session)


def _make_execution(status: str = "pending", **overrides) -> dict:
    defaults = {
        "id": uuid.uuid4(),
        "integration_system_id": TEST_SYSTEM_ID,
        "status": status,
        "date_from": date(2026, 3, 23),
        "date_to": date(2026, 3, 29),
        "triggered_by": "manual",
    }
    defaults.update(overrides)
    return defaults


async def test_create_execution(repo):
    data = _make_execution()
    execution = await repo.create(data)
    assert execution.id == data["id"]
    assert execution.status == "pending"
    assert execution.date_from == date(2026, 3, 23)


async def test_get_by_id(repo):
    data = _make_execution()
    await repo.create(data)

    found = await repo.get_by_id(data["id"])
    assert found is not None
    assert found.id == data["id"]


async def test_get_by_id_not_found(repo):
    found = await repo.get_by_id(uuid.uuid4())
    assert found is None


async def test_update_status(repo):
    data = _make_execution()
    await repo.create(data)

    updated = await repo.update_status(
        data["id"],
        "running",
        total_fetched=10,
        progress_data={"stage": "fetching"},
    )
    assert updated is not None
    assert updated.status == "running"
    assert updated.total_fetched == 10
    assert updated.progress_data == {"stage": "fetching"}


async def test_update_progress(repo):
    data = _make_execution()
    await repo.create(data)

    await repo.update_progress(data["id"], {"stage": "enriching", "count": 5})

    found = await repo.get_by_id(data["id"])
    assert found.progress_data == {"stage": "enriching", "count": 5}


async def test_list_by_system(repo):
    for _ in range(3):
        await repo.create(_make_execution())

    items, total = await repo.list_by_system(TEST_SYSTEM_ID, skip=0, limit=10)
    assert total == 3
    assert len(items) == 3


async def test_list_by_system_pagination(repo):
    for _ in range(5):
        await repo.create(_make_execution())

    items, total = await repo.list_by_system(TEST_SYSTEM_ID, skip=0, limit=2)
    assert total == 5
    assert len(items) == 2

    items2, _ = await repo.list_by_system(TEST_SYSTEM_ID, skip=2, limit=2)
    assert len(items2) == 2


async def test_list_all(repo):
    for _ in range(3):
        await repo.create(_make_execution())

    items, total = await repo.list_all(skip=0, limit=10)
    assert total == 3
    assert len(items) == 3


async def test_get_latest_by_system(repo):
    exec1 = _make_execution()
    exec2 = _make_execution()
    await repo.create(exec1)
    await repo.create(exec2)

    latest = await repo.get_latest_by_system(TEST_SYSTEM_ID)
    assert latest is not None


async def test_has_running_execution(repo):
    assert await repo.has_running_execution(TEST_SYSTEM_ID) is False

    await repo.create(_make_execution(status="running"))
    assert await repo.has_running_execution(TEST_SYSTEM_ID) is True


async def test_has_running_execution_pending_counts(repo):
    await repo.create(_make_execution(status="pending"))
    assert await repo.has_running_execution(TEST_SYSTEM_ID) is True


async def test_completed_does_not_count_as_running(repo):
    await repo.create(_make_execution(status="completed"))
    assert await repo.has_running_execution(TEST_SYSTEM_ID) is False
