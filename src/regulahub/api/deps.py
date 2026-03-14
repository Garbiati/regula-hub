import logging
from hmac import compare_digest

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from regulahub.config import get_auth_settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", description="API key for authentication")


async def verify_api_key(request: Request, api_key: str = Security(_api_key_header)) -> str:
    """Validate the API key from the X-API-Key header (timing-safe comparison)."""
    allowed = get_auth_settings().get_allowed_keys()
    if not any(compare_digest(api_key, key) for key in allowed):
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "Authentication failed: invalid API key from %s on %s %s",
            client_ip,
            request.method,
            request.url.path,
        )
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
