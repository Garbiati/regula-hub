import hashlib


def mask_username(username: str) -> str:
    """Return a short hash to identify the user in logs without exposing the username."""
    return hashlib.sha256(username.encode()).hexdigest()[:8]
