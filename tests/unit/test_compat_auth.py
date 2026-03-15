"""Tests for Absens-compatible authentication."""

import logging

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from regulahub.api.controllers.compat.absens_auth import verify_compat_auth
from regulahub.config import get_auth_settings

app = FastAPI()


@app.get("/test-auth")
async def test_endpoint(auth: str = Depends(verify_compat_auth)):
    return {"ok": True}


VALID_KEY = "test-api-key-12345"


@pytest.fixture(autouse=True)
def _set_api_keys(monkeypatch):
    monkeypatch.setenv("API_KEYS", VALID_KEY)
    get_auth_settings.cache_clear()
    yield
    get_auth_settings.cache_clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestVerifyCompatAuth:
    async def test_valid_key_passes(self, client):
        """T1: Valid Authorization header passes."""
        resp = await client.get("/test-auth", headers={"Authorization": VALID_KEY})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    async def test_missing_header_returns_401(self, client):
        """T2: Missing Authorization header returns 401."""
        resp = await client.get("/test-auth")
        assert resp.status_code == 401

    async def test_invalid_key_returns_401(self, client):
        """T3: Invalid key returns 401."""
        resp = await client.get("/test-auth", headers={"Authorization": "wrong-key"})
        assert resp.status_code == 401

    async def test_auth_failure_logs_warning(self, client, caplog):
        """T4: Auth failure logs a warning."""
        with caplog.at_level(logging.WARNING, logger="regulahub.api.controllers.compat.absens_auth"):
            await client.get("/test-auth", headers={"Authorization": "wrong-key"})
        assert any("invalid key" in record.message.lower() for record in caplog.records)
