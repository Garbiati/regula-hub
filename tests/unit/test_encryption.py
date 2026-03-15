"""Tests for utils/encryption.py — Fernet encrypt/decrypt."""

import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    """Provide a valid Fernet key for all tests in this module."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", key)
    # Clear cached settings/fernet so they pick up the new env
    from regulahub.config import get_credential_encryption_settings
    from regulahub.utils.encryption import _get_fernet

    get_credential_encryption_settings.cache_clear()
    _get_fernet.cache_clear()


def test_encrypt_decrypt_roundtrip():
    from regulahub.utils.encryption import decrypt_password, encrypt_password

    plaintext = "my_secret_p@ss"
    token = encrypt_password(plaintext)
    assert token != plaintext
    assert decrypt_password(token) == plaintext


def test_decrypt_invalid_token_raises():
    from regulahub.utils.encryption import decrypt_password

    with pytest.raises(ValueError, match="Failed to decrypt"):
        decrypt_password("not-a-valid-fernet-token")


def test_different_encryptions_produce_different_tokens():
    from regulahub.utils.encryption import encrypt_password

    t1 = encrypt_password("same_password")
    t2 = encrypt_password("same_password")
    # Fernet includes a timestamp + random IV, so tokens should differ
    assert t1 != t2
