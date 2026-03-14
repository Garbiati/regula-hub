"""Fernet (AES-128-CBC + HMAC) encrypt/decrypt for credential passwords."""

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


@lru_cache
def _get_fernet() -> Fernet:
    from regulahub.config import get_credential_encryption_settings

    key = get_credential_encryption_settings().credential_encryption_key
    return Fernet(key.encode())


def encrypt_password(plaintext: str) -> str:
    """Encrypt a plaintext password. Returns a base64 Fernet token string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_password(token: str) -> str:
    """Decrypt a Fernet token back to plaintext. Raises ValueError on failure."""
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt credential") from exc
