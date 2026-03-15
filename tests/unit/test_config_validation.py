"""Tests for config validation (Fernet key, pool settings)."""

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError


def _clear_caches():
    from regulahub.config import get_credential_encryption_settings

    get_credential_encryption_settings.cache_clear()


class TestCredentialEncryptionSettings:
    def setup_method(self):
        _clear_caches()

    def teardown_method(self):
        _clear_caches()

    def test_valid_fernet_key(self, monkeypatch):
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", key)
        _clear_caches()
        from regulahub.config import get_credential_encryption_settings

        settings = get_credential_encryption_settings()
        assert settings.credential_encryption_key == key

    def test_invalid_fernet_key_raises(self, monkeypatch):
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "x" * 44)
        _clear_caches()
        from regulahub.config import CredentialEncryptionSettings

        with pytest.raises(ValidationError, match="Invalid Fernet key"):
            CredentialEncryptionSettings()

    def test_short_key_raises(self, monkeypatch):
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "short")
        _clear_caches()
        from regulahub.config import CredentialEncryptionSettings

        with pytest.raises(ValidationError):
            CredentialEncryptionSettings()


class TestDatabaseSettings:
    def test_pool_defaults(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "test")
        monkeypatch.setenv("DB_PASSWORD", "test")
        from regulahub.config import DatabaseSettings

        settings = DatabaseSettings()
        assert settings.pool_size == 10
        assert settings.max_overflow == 20
        assert settings.pool_timeout == 10

    def test_pool_custom_values(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "test")
        monkeypatch.setenv("DB_PASSWORD", "test")
        monkeypatch.setenv("DB_POOL_SIZE", "20")
        monkeypatch.setenv("DB_MAX_OVERFLOW", "40")
        monkeypatch.setenv("DB_POOL_TIMEOUT", "30")
        from regulahub.config import DatabaseSettings

        settings = DatabaseSettings()
        assert settings.pool_size == 20
        assert settings.max_overflow == 40
        assert settings.pool_timeout == 30

    def test_pool_size_must_be_positive(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "test")
        monkeypatch.setenv("DB_PASSWORD", "test")
        monkeypatch.setenv("DB_POOL_SIZE", "0")
        from regulahub.config import DatabaseSettings

        with pytest.raises(ValidationError):
            DatabaseSettings()
