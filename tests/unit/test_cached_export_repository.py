"""Tests for CachedExportRepository using in-memory SQLite."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from regulahub.db.models import Base, CachedScheduleExport
from regulahub.db.repositories.cached_export import CachedExportRepository


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def repo(db_session):
    return CachedExportRepository(db_session)


def _make_row_dict(solicitacao: str = "SOL001", data_agendamento: str = "25/03/2026", **overrides) -> dict:
    defaults = {
        "solicitacao": solicitacao,
        "data_agendamento": data_agendamento,
        "data_agendamento_iso": date(2026, 3, 25),
        "descricao_procedimento": "TELECONSULTA EM DERMATOLOGIA",
        "row_data": {
            "solicitacao": solicitacao,
            "data_agendamento": data_agendamento,
            "descricao_procedimento": "TELECONSULTA EM DERMATOLOGIA",
            "nome": "PACIENTE TESTE",
            "cns": "111222333444555",
        },
    }
    defaults.update(overrides)
    return defaults


async def test_bulk_upsert_creates_new_rows(repo, db_session):
    rows = [_make_row_dict("SOL001"), _make_row_dict("SOL002")]
    count = await repo.bulk_upsert(rows)
    assert count == 2

    found = await repo.find_by_date_range(date(2026, 3, 1), date(2026, 3, 31))
    assert len(found) == 2


async def test_bulk_upsert_updates_existing(repo, db_session):
    await repo.bulk_upsert([_make_row_dict("SOL001")])
    await db_session.flush()

    updated_row = _make_row_dict("SOL001", row_data={"solicitacao": "SOL001", "updated": True})
    count = await repo.bulk_upsert([updated_row])
    assert count == 1

    found = await repo.find_by_date_range(date(2026, 3, 1), date(2026, 3, 31))
    assert len(found) == 1
    assert found[0].row_data.get("updated") is True


async def test_bulk_upsert_deduplicates(repo, db_session):
    await repo.bulk_upsert([_make_row_dict("SOL001")])
    await db_session.flush()
    await repo.bulk_upsert([_make_row_dict("SOL001")])

    found = await repo.find_by_date_range(date(2026, 3, 1), date(2026, 3, 31))
    assert len(found) == 1


async def test_find_by_date_range_filters_correctly(repo, db_session):
    rows = [
        _make_row_dict("SOL001", data_agendamento_iso=date(2026, 3, 10)),
        _make_row_dict("SOL002", data_agendamento_iso=date(2026, 3, 20)),
        _make_row_dict("SOL003", data_agendamento_iso=date(2026, 4, 5)),
    ]
    await repo.bulk_upsert(rows)
    await db_session.flush()

    found = await repo.find_by_date_range(date(2026, 3, 1), date(2026, 3, 31))
    assert len(found) == 2
    solicitacoes = {r.solicitacao for r in found}
    assert solicitacoes == {"SOL001", "SOL002"}


async def test_find_by_date_range_with_procedure_filter(repo, db_session):
    rows = [
        _make_row_dict("SOL001", descricao_procedimento="TELECONSULTA EM DERMATOLOGIA"),
        _make_row_dict("SOL002", descricao_procedimento="CONSULTA PRESENCIAL"),
    ]
    await repo.bulk_upsert(rows)
    await db_session.flush()

    found = await repo.find_by_date_range(date(2026, 3, 1), date(2026, 3, 31), procedure_filter="TELECONSULTA")
    assert len(found) == 1
    assert found[0].solicitacao == "SOL001"


async def test_find_excludes_inactive(repo, db_session):
    row = _make_row_dict("SOL001")
    await repo.bulk_upsert([row])
    await db_session.flush()

    # Deactivate the row
    from sqlalchemy import select

    stmt = select(CachedScheduleExport).where(CachedScheduleExport.solicitacao == "SOL001")
    result = await db_session.execute(stmt)
    entity = result.scalar_one()
    entity.is_active = False
    await db_session.flush()

    found = await repo.find_by_date_range(date(2026, 3, 1), date(2026, 3, 31))
    assert len(found) == 0


async def test_count_by_date_range(repo, db_session):
    rows = [_make_row_dict("SOL001"), _make_row_dict("SOL002"), _make_row_dict("SOL003")]
    await repo.bulk_upsert(rows)
    await db_session.flush()

    count = await repo.count_by_date_range(date(2026, 3, 1), date(2026, 3, 31))
    assert count == 3


async def test_count_with_procedure_filter(repo, db_session):
    rows = [
        _make_row_dict("SOL001", descricao_procedimento="TELECONSULTA EM DERMATOLOGIA"),
        _make_row_dict("SOL002", descricao_procedimento="CONSULTA PRESENCIAL"),
    ]
    await repo.bulk_upsert(rows)
    await db_session.flush()

    count = await repo.count_by_date_range(date(2026, 3, 1), date(2026, 3, 31), procedure_filter="TELECONSULTA")
    assert count == 1


async def test_empty_result_on_no_match(repo, db_session):
    found = await repo.find_by_date_range(date(2026, 1, 1), date(2026, 1, 31))
    assert found == []

    count = await repo.count_by_date_range(date(2026, 1, 1), date(2026, 1, 31))
    assert count == 0


async def test_bulk_upsert_preserves_enrichment_on_null_overwrite(repo, db_session):
    """When re-upserting a row without enrichment data, previously enriched fields are preserved."""
    enriched_row = _make_row_dict(
        "SOL001",
        row_data={
            "solicitacao": "SOL001",
            "data_agendamento": "25/03/2026",
            "descricao_procedimento": "TELECONSULTA EM DERMATOLOGIA",
            "nome": "PACIENTE TESTE",
            "cns": "111222333444555",
            "cpf_paciente": "123.456.789-00",
            "telefone_cadsus": "(11) 99999-0000",
            "email_paciente": "paciente@example.com",
        },
    )
    await repo.bulk_upsert([enriched_row])
    await db_session.flush()

    # Second upsert WITHOUT enrichment (simulating failed CADSUS)
    raw_row = _make_row_dict(
        "SOL001",
        row_data={
            "solicitacao": "SOL001",
            "data_agendamento": "25/03/2026",
            "descricao_procedimento": "TELECONSULTA EM DERMATOLOGIA",
            "nome": "PACIENTE TESTE",
            "cns": "111222333444555",
            "cpf_paciente": None,
            "telefone_cadsus": None,
            "email_paciente": None,
        },
    )
    await repo.bulk_upsert([raw_row])
    await db_session.flush()

    found = await repo.find_by_date_range(date(2026, 3, 1), date(2026, 3, 31))
    assert len(found) == 1
    row_data = found[0].row_data
    assert row_data["cpf_paciente"] == "123.456.789-00"
    assert row_data["telefone_cadsus"] == "(11) 99999-0000"
    assert row_data["email_paciente"] == "paciente@example.com"


async def test_bulk_upsert_updates_enrichment_when_new_data_present(repo, db_session):
    """When re-upserting with new enrichment data, the new data wins."""
    enriched_row = _make_row_dict(
        "SOL001",
        row_data={
            "solicitacao": "SOL001",
            "data_agendamento": "25/03/2026",
            "descricao_procedimento": "TELECONSULTA",
            "nome": "PACIENTE",
            "cns": "111222333444555",
            "cpf_paciente": "111.111.111-11",
            "telefone_cadsus": "(11) 11111-1111",
        },
    )
    await repo.bulk_upsert([enriched_row])
    await db_session.flush()

    # Re-upsert with updated enrichment
    updated_row = _make_row_dict(
        "SOL001",
        row_data={
            "solicitacao": "SOL001",
            "data_agendamento": "25/03/2026",
            "descricao_procedimento": "TELECONSULTA",
            "nome": "PACIENTE",
            "cns": "111222333444555",
            "cpf_paciente": "222.222.222-22",
            "telefone_cadsus": "(22) 22222-2222",
        },
    )
    await repo.bulk_upsert([updated_row])
    await db_session.flush()

    found = await repo.find_by_date_range(date(2026, 3, 1), date(2026, 3, 31))
    assert len(found) == 1
    row_data = found[0].row_data
    assert row_data["cpf_paciente"] == "222.222.222-22"
    assert row_data["telefone_cadsus"] == "(22) 22222-2222"
