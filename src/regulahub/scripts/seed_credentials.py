"""Seed credentials from an encrypted JSON file into the DB.

Reads the seed file, decrypts usernames, and upserts into credentials.
Passwords are stored as-is (already Fernet-encrypted in the seed file).
Idempotent on (user_id, profile_id, username).

Usage:
    python -m regulahub.scripts.seed_credentials
"""

import asyncio
import json
import logging
from pathlib import Path

from regulahub.config import get_seed_settings
from regulahub.db.engine import get_session_factory
from regulahub.db.repositories.credential import CredentialRepository
from regulahub.db.repositories.regulation_system import RegulationSystemRepository
from regulahub.utils.masking import mask_username

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_VERSION = 1


async def seed() -> None:
    seed_path = Path(get_seed_settings().seed_credentials_path)

    if not seed_path.exists():
        logger.info("No seed file at %s, skipping", seed_path)
        return

    try:
        from regulahub.utils.encryption import decrypt_password
    except Exception:
        logger.warning("Encryption key not configured, skipping credential seed")
        return

    try:
        raw = json.loads(seed_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read seed file %s: %s", seed_path, exc)
        return

    version = raw.get("version")
    if version != SUPPORTED_VERSION:
        logger.warning("Unsupported seed file version %s (expected %d), skipping", version, SUPPORTED_VERSION)
        return

    credentials = raw.get("credentials", [])
    if not credentials:
        logger.info("Seed file has no credentials, skipping")
        return

    factory = get_session_factory()
    seeded = 0

    async with factory() as session:
        cred_repo = CredentialRepository(session)
        sys_repo = RegulationSystemRepository(session)

        # Resolve first active user as the owner
        from sqlalchemy import select

        from regulahub.db.models import RegulaHubUser

        result = await session.execute(
            select(RegulaHubUser).where(RegulaHubUser.is_active.is_(True)).order_by(RegulaHubUser.created_at).limit(1)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("No active user found, skipping credential seed")
            return

        for entry in credentials:
            try:
                username = decrypt_password(entry["encrypted_username"])
            except (ValueError, KeyError) as exc:
                logger.warning("Failed to decrypt username in seed entry: %s, skipping", exc)
                continue

            profile_type = entry.get("profile_type", "")
            system = entry.get("system", "SISREG")

            # Resolve profile_id from system code + profile name
            profile_id = await sys_repo.resolve_profile_id(system, profile_type)
            if not profile_id:
                logger.warning("Cannot resolve profile for %s/%s, skipping", system, profile_type)
                continue

            existing = await cred_repo.get_by_user_profile_username(user.id, profile_id, username)
            if existing:
                logger.info(
                    "Credential [%s] %s/%s already exists, skipping", mask_username(username), profile_type, system
                )
                continue

            await cred_repo.create(
                {
                    "user_id": user.id,
                    "profile_id": profile_id,
                    "username": username,
                    "encrypted_password": entry["encrypted_password"],
                    "state": entry.get("state", ""),
                    "state_name": entry.get("state_name", ""),
                    "unit_name": entry.get("unit_name", ""),
                    "unit_cnes": entry.get("unit_cnes", ""),
                }
            )
            seeded += 1
            logger.info("Seeded credential [%s] %s/%s", mask_username(username), profile_type, system)

        await session.commit()

    logger.info("Credential seeding complete: %d new, %d total in file", seeded, len(credentials))


if __name__ == "__main__":
    asyncio.run(seed())
