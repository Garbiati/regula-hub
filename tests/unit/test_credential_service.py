"""Tests for services/credential_service.py — centralized credential resolution."""

import types
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet

from regulahub.services.credential_service import (
    CredentialNotFoundError,
    resolve_credential_by_cnes,
    resolve_credential_by_username,
    resolve_credentials_for_cnes_set,
    resolve_single_credential,
)

_REPO_PATH = "regulahub.db.repositories.credential.CredentialRepository"


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    """Provide a valid Fernet key for all tests in this module."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", key)
    from regulahub.config import get_credential_encryption_settings
    from regulahub.utils.encryption import _get_fernet

    get_credential_encryption_settings.cache_clear()
    _get_fernet.cache_clear()


def _make_cred(username="user1", encrypted_password=None, unit_cnes="1234567", unit_name="Unit A"):
    """Create a mock credential object."""
    from regulahub.utils.encryption import encrypt_password

    cred = types.SimpleNamespace()
    cred.username = username
    cred.encrypted_password = encrypted_password or encrypt_password("secret")
    cred.unit_cnes = unit_cnes
    cred.unit_name = unit_name
    return cred


class TestResolveSingleCredential:
    async def test_success_with_own_session(self):
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [_make_cred()]

        mock_session = AsyncMock()

        class FakeContextManager:
            async def __aenter__(self):
                return mock_session

            async def __aexit__(self, *args):
                pass

        def mock_factory():
            return FakeContextManager()

        with (
            patch(_REPO_PATH, return_value=mock_repo_instance),
            patch("regulahub.db.engine.get_session_factory", return_value=mock_factory),
        ):
            username, password = await resolve_single_credential("SISREG", "videofonista")

        assert username == "user1"
        assert password == "secret"

    async def test_success_with_provided_session(self):
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [_make_cred()]

        with patch(_REPO_PATH, return_value=mock_repo_instance):
            username, password = await resolve_single_credential("SISREG", "videofonista", db_session=AsyncMock())

        assert username == "user1"
        assert password == "secret"

    async def test_no_credentials_raises(self):
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = []

        with (
            patch(_REPO_PATH, return_value=mock_repo_instance),
            pytest.raises(CredentialNotFoundError, match="No videofonista credentials"),
        ):
            await resolve_single_credential("SISREG", "videofonista", db_session=AsyncMock())

    async def test_decrypt_failure_raises(self):
        cred = _make_cred(encrypted_password="not-a-valid-fernet-token")
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [cred]

        with (
            patch(_REPO_PATH, return_value=mock_repo_instance),
            pytest.raises(CredentialNotFoundError, match="Failed to decrypt"),
        ):
            await resolve_single_credential("SISREG", "videofonista", db_session=AsyncMock())


class TestResolveCredentialByCnes:
    async def test_success(self):
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [
            _make_cred(unit_cnes="1111111"),
            _make_cred(username="user2", unit_cnes="2222222"),
        ]

        with patch(_REPO_PATH, return_value=mock_repo_instance):
            username, password = await resolve_credential_by_cnes(
                "SISREG", "solicitante", "2222222", db_session=AsyncMock()
            )

        assert username == "user2"
        assert password == "secret"

    async def test_no_match_raises(self):
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [_make_cred(unit_cnes="9999999")]

        with (
            patch(_REPO_PATH, return_value=mock_repo_instance),
            pytest.raises(CredentialNotFoundError, match="No operator found"),
        ):
            await resolve_credential_by_cnes("SISREG", "solicitante", "0000000", db_session=AsyncMock())


class TestResolveCredentialByUsername:
    async def test_success(self):
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [
            _make_cred(username="video1"),
            _make_cred(username="video2"),
        ]

        with patch(_REPO_PATH, return_value=mock_repo_instance):
            username, password = await resolve_credential_by_username(
                "SISREG", "videofonista", "video2", db_session=AsyncMock()
            )

        assert username == "video2"
        assert password == "secret"

    async def test_no_match_raises(self):
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [_make_cred(username="other")]

        with (
            patch(_REPO_PATH, return_value=mock_repo_instance),
            pytest.raises(CredentialNotFoundError, match="No credential found for username"),
        ):
            await resolve_credential_by_username("SISREG", "videofonista", "missing", db_session=AsyncMock())

    async def test_decrypt_failure_raises(self):
        cred = _make_cred(username="bad", encrypted_password="not-a-valid-fernet-token")
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [cred]

        with (
            patch(_REPO_PATH, return_value=mock_repo_instance),
            pytest.raises(CredentialNotFoundError, match="Decryption failed for username"),
        ):
            await resolve_credential_by_username("SISREG", "videofonista", "bad", db_session=AsyncMock())


class TestResolveCredentialsForCnesSet:
    async def test_success(self):
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [
            _make_cred(username="u1", unit_cnes="111", unit_name="A"),
            _make_cred(username="u2", unit_cnes="222", unit_name="B"),
            _make_cred(username="u3", unit_cnes="333", unit_name="C"),
        ]

        with patch(_REPO_PATH, return_value=mock_repo_instance):
            result = await resolve_credentials_for_cnes_set(
                "SISREG", "solicitante", {"111", "333"}, db_session=AsyncMock()
            )

        assert len(result) == 2
        usernames = {r[0] for r in result}
        assert usernames == {"u1", "u3"}
        # Verify 4-tuple includes unit_cnes
        cnes_values = {r[3] for r in result}
        assert cnes_values == {"111", "333"}

    async def test_partial_decrypt_failure_skips(self):
        good_cred = _make_cred(username="good", unit_cnes="111", unit_name="Good")
        bad_cred = _make_cred(username="bad", unit_cnes="222", unit_name="Bad", encrypted_password="invalid-token")
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [good_cred, bad_cred]

        with patch(_REPO_PATH, return_value=mock_repo_instance):
            result = await resolve_credentials_for_cnes_set(
                "SISREG", "solicitante", {"111", "222"}, db_session=AsyncMock()
            )

        assert len(result) == 1
        assert result[0][0] == "good"

    async def test_all_fail_raises(self):
        bad_cred = _make_cred(unit_cnes="111", encrypted_password="invalid-token")
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_by_system_and_profile.return_value = [bad_cred]

        with (
            patch(_REPO_PATH, return_value=mock_repo_instance),
            pytest.raises(CredentialNotFoundError, match="No matching operators"),
        ):
            await resolve_credentials_for_cnes_set("SISREG", "solicitante", {"111"}, db_session=AsyncMock())
