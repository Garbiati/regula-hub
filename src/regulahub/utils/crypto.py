import hashlib


def hash_password(password: str) -> str:
    """Hash password using SHA-256 as expected by SisReg login.

    SisReg requires the password to be uppercased before hashing.
    """
    return hashlib.sha256(password.upper().encode()).hexdigest()
