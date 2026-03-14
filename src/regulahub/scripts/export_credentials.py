"""Export active credentials from DB into an encrypted seed file.

Reads active credentials (with joined profile/system data), encrypts usernames
(passwords are already encrypted), and writes a JSON file suitable for seeding
a fresh database.

Usage:
    python -m regulahub.scripts.export_credentials [--output docker/seed/credentials.enc.json]
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import select

from regulahub.db.engine import get_session_factory
from regulahub.db.models import Credential, System, SystemProfile
from regulahub.utils.encryption import encrypt_password
from regulahub.utils.masking import mask_username

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = "docker/seed/credentials.enc.json"


async def export_credentials(output_path: str) -> None:
    factory = get_session_factory()

    async with factory() as session:
        stmt = (
            select(Credential, SystemProfile.profile_name, System.code.label("system_code"))
            .join(SystemProfile, Credential.profile_id == SystemProfile.id)
            .join(System, SystemProfile.system_id == System.id)
            .where(Credential.is_active.is_(True))
            .order_by(SystemProfile.profile_name, Credential.username)
        )
        result = await session.execute(stmt)
        rows = result.all()

        if not rows:
            logger.warning("No active credentials found in DB, nothing to export")
            return

        entries = []
        for cred, profile_name, system_code in rows:
            entries.append(
                {
                    "encrypted_username": encrypt_password(cred.username),
                    "encrypted_password": cred.encrypted_password,
                    "profile_type": profile_name,
                    "system": system_code,
                    "state": cred.state,
                    "state_name": cred.state_name,
                    "unit_name": cred.unit_name or "",
                    "unit_cnes": cred.unit_cnes or "",
                }
            )
            logger.info("Exported credential [%s] %s/%s", mask_username(cred.username), profile_name, cred.state)

        seed_data = {
            "version": 1,
            "encrypted_with": "fernet",
            "credentials": entries,
        }

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(seed_data, indent=2, ensure_ascii=False) + "\n")
        logger.info("Exported %d credentials to %s", len(entries), out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export credentials to encrypted seed file")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help="Output file path")
    args = parser.parse_args()
    asyncio.run(export_credentials(args.output))


if __name__ == "__main__":
    main()
