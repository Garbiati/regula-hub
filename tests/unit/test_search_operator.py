"""Tests for the single-operator search endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from regulahub.sisreg.models import AppointmentListing, SearchResponse


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
    monkeypatch.setenv("API_KEYS", "test-key")
    monkeypatch.setenv("DB_USER", "test")
    monkeypatch.setenv("DB_PASSWORD", "test")
    _clear_all_caches()
    yield
    _clear_all_caches()


@pytest.fixture
def client():
    from regulahub.main import app

    app.router.lifespan_context = None
    return TestClient(app, raise_server_exceptions=False)


HEADERS = {"X-API-Key": "test-key"}

SAMPLE_ITEM = AppointmentListing(
    code="SOL-001",
    request_date="01/01/2026",
    risk=3,
    patient_name="Test Patient",
    phone="92999999999",
    municipality="Manaus",
    age="30",
    procedure="Consulta",
    cid="Z00",
    dept_solicitation="UBS Centro",
    dept_execute="Hospital Geral",
    execution_date="",
    status="Agendada",
)


@patch("regulahub.api.controllers.admin.sisreg_routes.resolve_credential_by_username")
@patch("regulahub.api.controllers.admin.sisreg_routes.SisregClient")
def test_search_operator_returns_single_operator_result(mock_client_cls, mock_resolve, client):
    """Single-operator endpoint returns OperatorSearchResponse with operator field."""
    mock_resolve.return_value = ("op1", "pass1")

    mock_client = AsyncMock()
    mock_client.search.return_value = SearchResponse(items=[SAMPLE_ITEM], total=1)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    resp = client.post(
        "/api/admin/sisreg/search-operator",
        json={
            "date_from": "01/01/2026",
            "date_to": "31/01/2026",
            "profile_type": "VIDEOFONISTA",
            "usernames": ["op1"],
        },
        headers=HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["operator"] == "op1"
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["code"] == "SOL-001"


@patch("regulahub.api.controllers.admin.sisreg_routes.resolve_credential_by_username")
def test_search_operator_rejects_multiple_usernames(mock_resolve, client):
    """Endpoint rejects requests with more than one username."""
    resp = client.post(
        "/api/admin/sisreg/search-operator",
        json={
            "date_from": "01/01/2026",
            "date_to": "31/01/2026",
            "profile_type": "VIDEOFONISTA",
            "usernames": ["op1", "op2"],
        },
        headers=HEADERS,
    )
    assert resp.status_code == 422
    assert "Exactly one username" in resp.json()["detail"]


@patch("regulahub.api.controllers.admin.sisreg_routes.resolve_credential_by_username")
def test_search_operator_credential_not_found(mock_resolve, client):
    """Endpoint returns 404 when credential is not found."""
    from regulahub.services.credential_service import CredentialNotFoundError

    mock_resolve.side_effect = CredentialNotFoundError("Not found")

    resp = client.post(
        "/api/admin/sisreg/search-operator",
        json={
            "date_from": "01/01/2026",
            "date_to": "31/01/2026",
            "profile_type": "VIDEOFONISTA",
            "usernames": ["unknown"],
        },
        headers=HEADERS,
    )
    assert resp.status_code == 404


@patch("regulahub.api.controllers.admin.sisreg_routes.resolve_credential_by_username")
@patch("regulahub.api.controllers.admin.sisreg_routes.SisregClient")
def test_search_operator_login_failure(mock_client_cls, mock_resolve, client):
    """Endpoint returns 502 on SisReg login failure."""
    from regulahub.sisreg.client import SisregLoginError

    mock_resolve.return_value = ("op1", "pass1")

    mock_client = AsyncMock()
    mock_client.search.side_effect = SisregLoginError("Login failed")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    resp = client.post(
        "/api/admin/sisreg/search-operator",
        json={
            "date_from": "01/01/2026",
            "date_to": "31/01/2026",
            "profile_type": "VIDEOFONISTA",
            "usernames": ["op1"],
        },
        headers=HEADERS,
    )
    assert resp.status_code == 502
    assert "login failed" in resp.json()["detail"]
