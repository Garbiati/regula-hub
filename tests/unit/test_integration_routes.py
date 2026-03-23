"""Tests for integration worker API routes."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from regulahub.api.controllers.admin.integration_routes import router
from regulahub.api.rate_limit import limiter
from regulahub.config import get_auth_settings
from regulahub.db.engine import get_session

VALID_KEY = "test-api-key-integration"

app = FastAPI()
app.include_router(router)


@pytest.fixture(autouse=True)
def _set_api_keys(monkeypatch):
    monkeypatch.setenv("API_KEYS", VALID_KEY)
    monkeypatch.setenv("DB_USER", "test")
    monkeypatch.setenv("DB_PASSWORD", "test")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_NAME", "test")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "dGVzdC1rZXktZm9yLWNpLXBpcGVsaW5lLTMyYnl0ZXM=")
    get_auth_settings.cache_clear()
    limiter.enabled = False
    yield
    limiter.enabled = True
    get_auth_settings.cache_clear()
    app.dependency_overrides.clear()


def _mock_db_session():
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session
    return mock_session


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _auth_headers():
    return {"X-API-Key": VALID_KEY}


class TestTriggerExecution:
    async def test_invalid_date_range_returns_422(self, client):
        _mock_db_session()
        resp = await client.post(
            "/api/admin/integrations/execute",
            headers=_auth_headers(),
            json={"system_code": "TEST", "date_from": "2026-03-29", "date_to": "2026-03-23"},
        )
        assert resp.status_code == 422

    async def test_system_not_found_returns_404(self, client):
        _mock_db_session()
        with patch(
            "regulahub.api.controllers.admin.integration_routes.trigger_execution",
            side_effect=ValueError("Integration system 'NONEXISTENT' not found"),
        ):
            resp = await client.post(
                "/api/admin/integrations/execute",
                headers=_auth_headers(),
                json={"system_code": "NONEXISTENT", "date_from": "2026-03-23", "date_to": "2026-03-29"},
            )
            assert resp.status_code == 404

    async def test_already_running_returns_409(self, client):
        _mock_db_session()
        with patch(
            "regulahub.api.controllers.admin.integration_routes.trigger_execution",
            side_effect=RuntimeError("An execution is already running for system 'TEST'"),
        ):
            resp = await client.post(
                "/api/admin/integrations/execute",
                headers=_auth_headers(),
                json={"system_code": "TEST", "date_from": "2026-03-23", "date_to": "2026-03-29"},
            )
            assert resp.status_code == 409

    async def test_successful_trigger_returns_202(self, client):
        _mock_db_session()
        execution_id = uuid.uuid4()

        with patch(
            "regulahub.api.controllers.admin.integration_routes.trigger_execution",
            return_value=execution_id,
        ):
            resp = await client.post(
                "/api/admin/integrations/execute",
                headers=_auth_headers(),
                json={"system_code": "TEST", "date_from": "2026-03-23", "date_to": "2026-03-29"},
            )
            assert resp.status_code == 202
            data = resp.json()
            assert data["id"] == str(execution_id)
            assert data["status"] == "pending"


class TestGetExecutionStatus:
    async def test_not_found_returns_404(self, client):
        _mock_db_session()
        fake_id = uuid.uuid4()

        with (
            patch(
                "regulahub.api.controllers.admin.integration_routes.get_execution_progress",
                return_value=None,
            ),
            patch(
                "regulahub.api.controllers.admin.integration_routes.IntegrationExecutionRepository"
            ) as mock_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            resp = await client.get(
                f"/api/admin/integrations/executions/{fake_id}/status",
                headers=_auth_headers(),
            )
            assert resp.status_code == 404


class TestListExecutions:
    async def test_empty_list(self, client):
        _mock_db_session()

        with patch(
            "regulahub.api.controllers.admin.integration_routes.IntegrationExecutionRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.list_all = AsyncMock(return_value=([], 0))

            resp = await client.get(
                "/api/admin/integrations/executions",
                headers=_auth_headers(),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["items"] == []
            assert data["total"] == 0


class TestCancelExecution:
    async def test_cancel_not_found_returns_404(self, client):
        fake_id = uuid.uuid4()
        with patch(
            "regulahub.api.controllers.admin.integration_routes.cancel_execution",
            return_value=False,
        ):
            resp = await client.post(
                f"/api/admin/integrations/executions/{fake_id}/cancel",
                headers=_auth_headers(),
            )
            assert resp.status_code == 404

    async def test_cancel_success(self, client):
        fake_id = uuid.uuid4()
        with patch(
            "regulahub.api.controllers.admin.integration_routes.cancel_execution",
            return_value=True,
        ):
            resp = await client.post(
                f"/api/admin/integrations/executions/{fake_id}/cancel",
                headers=_auth_headers(),
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "cancelling"


class TestAuth:
    async def test_missing_api_key_returns_401(self, client):
        resp = await client.get("/api/admin/integrations/systems")
        assert resp.status_code in (401, 403)

    async def test_invalid_api_key_returns_401(self, client):
        resp = await client.get(
            "/api/admin/integrations/systems",
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401
