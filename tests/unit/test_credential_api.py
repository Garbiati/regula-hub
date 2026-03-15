"""Tests for credential admin API endpoints."""

import uuid

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

# Fixed IDs for test seed data
REG_TYPE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SISREG_ID = uuid.UUID("22910218-c8b6-40fe-9e38-d971b609c155")
VF_PROFILE_ID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000001")
SOL_PROFILE_ID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000002")
USER_ID = uuid.UUID("b3a7c9e1-4f2d-4e8a-9c1b-5d6f7a8b9c0e")


def _clear_all_caches():
    """Clear all lru_cache singletons so env changes take effect."""
    from regulahub.config import (
        get_auth_settings,
        get_credential_encryption_settings,
        get_database_settings,
        get_seed_settings,
        get_settings,
    )
    from regulahub.utils.encryption import _get_fernet

    for fn in [
        get_auth_settings,
        get_credential_encryption_settings,
        get_database_settings,
        get_settings,
        get_seed_settings,
        _get_fernet,
    ]:
        fn.cache_clear()


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Set required env vars for the app."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", key)
    monkeypatch.setenv("API_KEYS", "test-key")
    monkeypatch.setenv("DB_USER", "test")
    monkeypatch.setenv("DB_PASSWORD", "test")
    _clear_all_caches()
    yield
    _clear_all_caches()


@pytest.fixture
def _mock_db(monkeypatch):
    """Mock get_session dependency to use in-memory SQLite with seed data."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from regulahub.db.models import Base, RegulaHubUser, System, SystemProfile, SystemType

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _initialized = False

    async def _init_db():
        nonlocal _initialized
        if _initialized:
            return
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as session:
            session.add(
                RegulaHubUser(
                    id=USER_ID,
                    name="Test User",
                    email="test@example.com",
                    login="testuser",
                )
            )
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
            await session.commit()
        _initialized = True

    async def _get_session():
        await _init_db()
        async with factory() as session:
            yield session

    from regulahub.db import engine as engine_module

    monkeypatch.setattr(engine_module, "get_session", _get_session)
    return engine


@pytest.fixture
def client(_mock_db):
    # Disable lifespan to avoid scheduler/db init issues
    from regulahub.main import app

    app.router.lifespan_context = None
    return TestClient(app, raise_server_exceptions=False)


HEADERS = {"X-API-Key": "test-key"}


def test_create_credential(client):
    resp = client.post(
        "/api/admin/credentials",
        json={
            "user_id": str(USER_ID),
            "profile_id": str(VF_PROFILE_ID),
            "username": "test_user",
            "password": "secret123",
            "state": "AM",
            "state_name": "Amazonas",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "test_user"
    assert data["profile_name"] == "VIDEOFONISTA"
    assert data["system_code"] == "SISREG"
    assert "password" not in data
    assert "encrypted_password" not in data


def test_create_duplicate_credential(client):
    payload = {
        "user_id": str(USER_ID),
        "profile_id": str(VF_PROFILE_ID),
        "username": "dup_user",
        "password": "pass",
        "state": "AM",
        "state_name": "Amazonas",
    }
    resp1 = client.post("/api/admin/credentials", json=payload, headers=HEADERS)
    assert resp1.status_code == 201

    resp2 = client.post("/api/admin/credentials", json=payload, headers=HEADERS)
    assert resp2.status_code == 409


def test_list_credentials(client):
    client.post(
        "/api/admin/credentials",
        json={
            "user_id": str(USER_ID),
            "profile_id": str(VF_PROFILE_ID),
            "username": "list_user",
            "password": "pass",
            "state": "AM",
            "state_name": "Amazonas",
        },
        headers=HEADERS,
    )
    resp = client.get("/api/admin/credentials?system=SISREG", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_update_credential(client):
    resp = client.post(
        "/api/admin/credentials",
        json={
            "user_id": str(USER_ID),
            "profile_id": str(VF_PROFILE_ID),
            "username": "upd_user",
            "password": "pass",
            "state": "AM",
            "state_name": "Amazonas",
        },
        headers=HEADERS,
    )
    cred_id = resp.json()["id"]

    resp2 = client.put(
        f"/api/admin/credentials/{cred_id}",
        json={"state": "SP", "state_name": "São Paulo"},
        headers=HEADERS,
    )
    assert resp2.status_code == 200
    assert resp2.json()["state"] == "SP"


def test_delete_credential(client):
    resp = client.post(
        "/api/admin/credentials",
        json={
            "user_id": str(USER_ID),
            "profile_id": str(VF_PROFILE_ID),
            "username": "del_user",
            "password": "pass",
            "state": "AM",
            "state_name": "Amazonas",
        },
        headers=HEADERS,
    )
    cred_id = resp.json()["id"]

    resp2 = client.delete(f"/api/admin/credentials/{cred_id}", headers=HEADERS)
    assert resp2.status_code == 204


def test_list_states(client):
    client.post(
        "/api/admin/credentials",
        json={
            "user_id": str(USER_ID),
            "profile_id": str(VF_PROFILE_ID),
            "username": "state_user",
            "password": "pass",
            "state": "AM",
            "state_name": "Amazonas",
        },
        headers=HEADERS,
    )
    resp = client.get("/api/admin/credentials/states?system=SISREG", headers=HEADERS)
    assert resp.status_code == 200
    states = resp.json()
    assert any(s["state"] == "AM" for s in states)


def test_list_profiles(client):
    resp = client.get("/api/admin/credentials/profiles?system=SISREG", headers=HEADERS)
    assert resp.status_code == 200
    profiles = resp.json()
    assert len(profiles) >= 1
    assert all("name" in p and "description" in p for p in profiles)
