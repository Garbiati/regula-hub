"""Tests for authentication, request ID, and security headers middleware."""

import uuid

import pytest
from cryptography.fernet import Fernet

# Reuse the same test constants from test_credential_api for consistency
REG_TYPE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SISREG_ID = uuid.UUID("22910218-c8b6-40fe-9e38-d971b609c155")
VF_PROFILE_ID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000001")
SOL_PROFILE_ID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000002")
USER_ID = uuid.UUID("b3a7c9e1-4f2d-4e8a-9c1b-5d6f7a8b9c0e")


def _clear_all_caches():
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
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", key)
    monkeypatch.setenv("API_KEYS", "test-key-auth")
    monkeypatch.setenv("DB_USER", "test")
    monkeypatch.setenv("DB_PASSWORD", "test")
    _clear_all_caches()
    yield
    _clear_all_caches()


@pytest.fixture
def _mock_db(monkeypatch):
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
            session.add(RegulaHubUser(id=USER_ID, name="Test User", email="test@example.com", login="testuser"))
            session.add(SystemType(id=REG_TYPE_ID, code="regulation", name="Regulation"))
            session.add(
                System(
                    id=SISREG_ID,
                    system_type_id=REG_TYPE_ID,
                    code="SISREG",
                    name="SisReg",
                    table_prefix="sisreg",
                )
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
    from regulahub.main import app

    app.router.lifespan_context = None
    from fastapi.testclient import TestClient

    return TestClient(app, raise_server_exceptions=False)


HEADERS = {"X-API-Key": "test-key-auth"}


def test_invalid_api_key_returns_401(client):
    resp = client.get("/api/admin/credentials?system=SISREG", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


def test_missing_api_key_returns_403(client):
    resp = client.get("/api/admin/credentials?system=SISREG")
    assert resp.status_code == 403


def test_valid_api_key_passes(client):
    resp = client.get("/api/admin/credentials?system=SISREG", headers=HEADERS)
    assert resp.status_code == 200


def test_request_id_generated_in_response(client):
    resp = client.get("/api/admin/credentials?system=SISREG", headers=HEADERS)
    assert "X-Request-ID" in resp.headers
    # Verify it looks like a UUID
    uuid.UUID(resp.headers["X-Request-ID"])


def test_request_id_forwarded_when_provided(client):
    custom_id = str(uuid.uuid4())
    resp = client.get(
        "/api/admin/credentials?system=SISREG",
        headers={**HEADERS, "X-Request-ID": custom_id},
    )
    assert resp.headers.get("X-Request-ID") == custom_id


def test_security_headers_present(client):
    resp = client.get("/api/admin/credentials?system=SISREG", headers=HEADERS)
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "max-age" in resp.headers.get("Strict-Transport-Security", "")
    assert resp.headers.get("Cache-Control") == "no-store"
