"""Tests for form metadata service and API endpoints."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from regulahub.db.models import Base, System, SystemEndpoint, SystemType
from regulahub.db.repositories.regulation_system import RegulationSystemRepository
from regulahub.services import form_metadata as fm_service

REG_TYPE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SISREG_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")

SAMPLE_FORM_METADATA = {
    "version": 1,
    "updated_at": "2026-03-16T00:00:00Z",
    "search_types": [
        {"value": "solicitacao", "label_key": "consulta.type_solicitacao", "canonical_label": "Solicitação"},
        {"value": "agendamento", "label_key": "consulta.type_agendamento", "canonical_label": "Agendamento"},
    ],
    "situations": [
        {
            "value": "1",
            "label_key": "consulta.sit_sol_pending_regulation",
            "canonical_label": "Solicitação / Pendente / Regulação",
            "applies_to": ["solicitacao"],
        },
        {
            "value": "7",
            "label_key": "consulta.sit_sol_scheduled",
            "canonical_label": "Solicitação / Agendada",
            "applies_to": ["solicitacao", "agendamento", "execucao"],
        },
    ],
    "items_per_page": [
        {"value": "20", "label": "20"},
        {"value": "0", "label_key": "consulta.items_all", "canonical_label": "TODOS"},
    ],
    "defaults": {"search_type": "agendamento", "situation": "7", "items_per_page": "20"},
}


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        session.add(SystemType(id=REG_TYPE_ID, code="regulation", name="Regulation"))
        await session.flush()

        session.add(
            System(
                id=SISREG_ID,
                system_type_id=REG_TYPE_ID,
                code="SISREG",
                name="SisReg",
                table_prefix="sisreg",
            )
        )
        await session.flush()
        yield session

    # Clear module-level cache between tests
    fm_service._cache.clear()
    await engine.dispose()


@pytest.fixture
def repo(db_session):
    return RegulationSystemRepository(db_session)


async def _create_endpoint(session: AsyncSession, config: dict | None = None) -> SystemEndpoint:
    endpoint = SystemEndpoint(
        system_id=SISREG_ID,
        name="search_appointments",
        protocol="WEB",
        http_method="GET",
        path="/cgi-bin/gerenciador_solicitacao",
        config=config,
    )
    session.add(endpoint)
    await session.flush()
    return endpoint


# ── Repository tests ──────────────────────────────────────────────────


async def test_get_endpoint_by_system_and_name(repo, db_session):
    await _create_endpoint(db_session, config={"query_params": {"etapa": "PESQUISAR"}})

    ep = await repo.get_endpoint_by_system_and_name("SISREG", "search_appointments")
    assert ep is not None
    assert ep.name == "search_appointments"
    assert ep.config["query_params"]["etapa"] == "PESQUISAR"


async def test_get_endpoint_not_found(repo):
    ep = await repo.get_endpoint_by_system_and_name("SISREG", "nonexistent")
    assert ep is None


async def test_update_endpoint_config(repo, db_session):
    ep = await _create_endpoint(db_session, config={"old_key": True})

    new_config = {"old_key": True, "form_metadata": SAMPLE_FORM_METADATA}
    updated = await repo.update_endpoint_config(ep.id, new_config)
    assert updated is not None
    assert updated.config["form_metadata"]["version"] == 1
    assert updated.updated_at is not None


async def test_update_endpoint_config_nonexistent(repo):
    result = await repo.update_endpoint_config(uuid.uuid4(), {"foo": "bar"})
    assert result is None


# ── Service tests ─────────────────────────────────────────────────────


async def test_get_form_metadata_returns_data(db_session):
    fm_service._cache.clear()
    config = {"query_params": {"etapa": "PESQUISAR"}, "form_metadata": SAMPLE_FORM_METADATA}
    await _create_endpoint(db_session, config=config)

    data, etag = await fm_service.get_form_metadata(db_session, "SISREG", "search_appointments")
    assert data is not None
    assert data["version"] == 1
    assert len(data["situations"]) == 2
    assert etag is not None


async def test_get_form_metadata_not_found(db_session):
    fm_service._cache.clear()
    data, etag = await fm_service.get_form_metadata(db_session, "SISREG", "nonexistent")
    assert data is None
    assert etag is None


async def test_get_form_metadata_no_form_metadata_key(db_session):
    fm_service._cache.clear()
    await _create_endpoint(db_session, config={"query_params": {"etapa": "PESQUISAR"}})

    data, etag = await fm_service.get_form_metadata(db_session, "SISREG", "search_appointments")
    assert data is None
    assert etag is None


async def test_get_form_metadata_uses_cache(db_session):
    fm_service._cache.clear()
    config = {"form_metadata": SAMPLE_FORM_METADATA}
    await _create_endpoint(db_session, config=config)

    # First call populates cache
    data1, etag1 = await fm_service.get_form_metadata(db_session, "SISREG", "search_appointments")
    # Second call should hit cache (same etag)
    data2, etag2 = await fm_service.get_form_metadata(db_session, "SISREG", "search_appointments")
    assert data1 == data2
    assert etag1 == etag2


async def test_invalidate_cache(db_session):
    fm_service._cache.clear()
    config = {"form_metadata": SAMPLE_FORM_METADATA}
    await _create_endpoint(db_session, config=config)

    await fm_service.get_form_metadata(db_session, "SISREG", "search_appointments")
    key = fm_service._cache_key("SISREG", "search_appointments")
    assert key in fm_service._cache

    fm_service.invalidate_cache("SISREG", "search_appointments")
    assert key not in fm_service._cache


async def test_update_form_metadata(db_session):
    fm_service._cache.clear()
    config = {"query_params": {"etapa": "PESQUISAR"}, "form_metadata": SAMPLE_FORM_METADATA}
    await _create_endpoint(db_session, config=config)

    update_data = {
        "situations": [
            {"value": "99", "label_key": "consulta.sit_new", "canonical_label": "New Situation"},
        ],
    }
    result = await fm_service.update_form_metadata(db_session, "SISREG", "search_appointments", update_data)
    assert result is not None
    assert result["version"] == 2  # auto-incremented
    assert len(result["situations"]) == 1
    assert result["situations"][0]["value"] == "99"
    # Other fields preserved
    assert len(result["search_types"]) == 2
    assert result["updated_at"] is not None


async def test_update_form_metadata_with_explicit_version(db_session):
    fm_service._cache.clear()
    config = {"form_metadata": SAMPLE_FORM_METADATA}
    await _create_endpoint(db_session, config=config)

    result = await fm_service.update_form_metadata(db_session, "SISREG", "search_appointments", {"version": 42})
    assert result is not None
    assert result["version"] == 42


async def test_update_form_metadata_not_found(db_session):
    fm_service._cache.clear()
    result = await fm_service.update_form_metadata(db_session, "SISREG", "nonexistent", {"version": 2})
    assert result is None


async def test_update_invalidates_cache(db_session):
    fm_service._cache.clear()
    config = {"form_metadata": SAMPLE_FORM_METADATA}
    await _create_endpoint(db_session, config=config)

    # Populate cache
    await fm_service.get_form_metadata(db_session, "SISREG", "search_appointments")
    key = fm_service._cache_key("SISREG", "search_appointments")
    assert key in fm_service._cache

    # Update should invalidate
    await fm_service.update_form_metadata(db_session, "SISREG", "search_appointments", {"version": 5})
    assert key not in fm_service._cache
