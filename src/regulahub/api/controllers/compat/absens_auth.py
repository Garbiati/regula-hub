"""Authentication for Absens-compatible endpoints.

The regulation-service sends credentials via the standard Authorization header
(not X-API-Key used by admin endpoints). This module provides isolated auth
that reads the Authorization header and validates against the same API keys.
"""

import logging
from hmac import compare_digest

from fastapi import HTTPException, Request

from regulahub.config import get_auth_settings

logger = logging.getLogger(__name__)


async def verify_compat_auth(request: Request) -> str:
    """Validate the API key from the Authorization header (timing-safe comparison)."""
    auth_value = request.headers.get("Authorization")
    if not auth_value:
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "Compat auth failed: missing Authorization header from %s on %s %s",
            client_ip,
            request.method,
            request.url.path,
        )
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    allowed = get_auth_settings().get_allowed_keys()
    if not any(compare_digest(auth_value, key) for key in allowed):
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "Compat auth failed: invalid key from %s on %s %s",
            client_ip,
            request.method,
            request.url.path,
        )
        raise HTTPException(status_code=401, detail="Invalid API key")

    return auth_value
