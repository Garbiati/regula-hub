"""Form metadata service — reads/updates form_metadata from system_endpoints.config JSONB.

Uses an in-process dict cache with TTL to avoid hitting the DB on every request.
"""

import hashlib
import json
import logging
import time
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.db.repositories.regulation_system import RegulationSystemRepository

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300  # 5 minutes

# key -> (expiry_monotonic, data_dict, etag_str)
_cache: dict[str, tuple[float, dict, str]] = {}


def _cache_key(system_code: str, endpoint_name: str) -> str:
    return f"{system_code}:{endpoint_name}"


def _compute_etag(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324


def invalidate_cache(system_code: str, endpoint_name: str) -> None:
    """Remove a specific entry from the in-process cache."""
    key = _cache_key(system_code, endpoint_name)
    _cache.pop(key, None)


async def get_form_metadata(
    session: AsyncSession,
    system_code: str,
    endpoint_name: str,
) -> tuple[dict | None, str | None]:
    """Return (form_metadata_dict, etag) or (None, None) if not found.

    Serves from in-process cache when TTL has not expired.
    """
    key = _cache_key(system_code, endpoint_name)
    now = time.monotonic()

    cached = _cache.get(key)
    if cached is not None:
        expiry, data, etag = cached
        if now < expiry:
            return data, etag

    repo = RegulationSystemRepository(session)
    endpoint = await repo.get_endpoint_by_system_and_name(system_code, endpoint_name)
    if not endpoint or not endpoint.config:
        return None, None

    form_metadata = endpoint.config.get("form_metadata")
    if not form_metadata:
        return None, None

    etag = _compute_etag(form_metadata)
    _cache[key] = (now + CACHE_TTL_SECONDS, form_metadata, etag)
    return form_metadata, etag


async def update_form_metadata(
    session: AsyncSession,
    system_code: str,
    endpoint_name: str,
    update_data: dict,
) -> dict | None:
    """Merge update_data into the existing form_metadata and persist.

    Returns the updated form_metadata dict or None if system/endpoint not found.
    """
    repo = RegulationSystemRepository(session)
    endpoint = await repo.get_endpoint_by_system_and_name(system_code, endpoint_name)
    if not endpoint:
        return None

    config = dict(endpoint.config or {})
    existing = dict(config.get("form_metadata", {}))

    # Merge only provided fields
    for field in ("search_types", "situations", "items_per_page", "defaults"):
        if field in update_data and update_data[field] is not None:
            existing[field] = update_data[field]

    if "version" in update_data and update_data["version"] is not None:
        existing["version"] = update_data["version"]
    else:
        existing["version"] = existing.get("version", 0) + 1

    existing["updated_at"] = datetime.now(UTC).isoformat()
    config["form_metadata"] = existing

    await repo.update_endpoint_config(endpoint.id, config)
    invalidate_cache(system_code, endpoint_name)
    logger.info("Form metadata updated for %s/%s (version %s)", system_code, endpoint_name, existing["version"])
    return existing
