"""Seed demo credentials for non-SISREG systems (ESUS, SIGA, CARE, SER).

Guarded by SEED_DEMO_CREDENTIALS=true env var.
Passwords are Fernet-encrypted dummy values — never used for real login.
Idempotent via unique constraint on (user_id, profile_id, username).

Usage:
    python -m regulahub.scripts.seed_demo_credentials
"""

import asyncio
import logging
import os

from regulahub.db.engine import get_session_factory
from regulahub.db.repositories.credential import CredentialRepository
from regulahub.db.repositories.regulation_system import RegulationSystemRepository
from regulahub.utils.encryption import encrypt_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEMO_CREDENTIALS: list[dict] = [
    # ESUS
    {
        "username": "demo.esus.regulador.am.01",
        "profile_type": "REGULADOR",
        "system": "ESUS",
        "state": "AM",
        "state_name": "Amazonas",
    },
    {
        "username": "demo.esus.regulador.sp.01",
        "profile_type": "REGULADOR",
        "system": "ESUS",
        "state": "SP",
        "state_name": "São Paulo",
    },
    {
        "username": "demo.esus.solicitante.am.01",
        "profile_type": "SOLICITANTE",
        "system": "ESUS",
        "state": "AM",
        "state_name": "Amazonas",
    },
    {
        "username": "demo.esus.solicitante.mg.01",
        "profile_type": "SOLICITANTE",
        "system": "ESUS",
        "state": "MG",
        "state_name": "Minas Gerais",
    },
    {
        "username": "demo.esus.executante.am.01",
        "profile_type": "EXECUTANTE",
        "system": "ESUS",
        "state": "AM",
        "state_name": "Amazonas",
    },
    {
        "username": "demo.esus.executante.sp.01",
        "profile_type": "EXECUTANTE",
        "system": "ESUS",
        "state": "SP",
        "state_name": "São Paulo",
    },
    # SIGA
    {
        "username": "demo.siga.regulador.sp.01",
        "profile_type": "REGULADOR",
        "system": "SIGA",
        "state": "SP",
        "state_name": "São Paulo",
    },
    {
        "username": "demo.siga.regulador.sp.02",
        "profile_type": "REGULADOR",
        "system": "SIGA",
        "state": "SP",
        "state_name": "São Paulo",
    },
    {
        "username": "demo.siga.solicitante.sp.01",
        "profile_type": "SOLICITANTE",
        "system": "SIGA",
        "state": "SP",
        "state_name": "São Paulo",
    },
    {
        "username": "demo.siga.gestor.sp.01",
        "profile_type": "GESTOR",
        "system": "SIGA",
        "state": "SP",
        "state_name": "São Paulo",
    },
    {
        "username": "demo.siga.gestor.sp.02",
        "profile_type": "GESTOR",
        "system": "SIGA",
        "state": "SP",
        "state_name": "São Paulo",
    },
    # CARE
    {
        "username": "demo.care.regulador.pr.01",
        "profile_type": "REGULADOR",
        "system": "CARE",
        "state": "PR",
        "state_name": "Paraná",
    },
    {
        "username": "demo.care.regulador.pr.02",
        "profile_type": "REGULADOR",
        "system": "CARE",
        "state": "PR",
        "state_name": "Paraná",
    },
    {
        "username": "demo.care.solicitante.pr.01",
        "profile_type": "SOLICITANTE",
        "system": "CARE",
        "state": "PR",
        "state_name": "Paraná",
    },
    {
        "username": "demo.care.auditor.pr.01",
        "profile_type": "AUDITOR",
        "system": "CARE",
        "state": "PR",
        "state_name": "Paraná",
    },
    {
        "username": "demo.care.auditor.pr.02",
        "profile_type": "AUDITOR",
        "system": "CARE",
        "state": "PR",
        "state_name": "Paraná",
    },
    # SER
    {
        "username": "demo.ser.regulador.rj.01",
        "profile_type": "REGULADOR",
        "system": "SER",
        "state": "RJ",
        "state_name": "Rio de Janeiro",
    },
    {
        "username": "demo.ser.regulador.rj.02",
        "profile_type": "REGULADOR",
        "system": "SER",
        "state": "RJ",
        "state_name": "Rio de Janeiro",
    },
    {
        "username": "demo.ser.solicitante.rj.01",
        "profile_type": "SOLICITANTE",
        "system": "SER",
        "state": "RJ",
        "state_name": "Rio de Janeiro",
    },
    {
        "username": "demo.ser.executor.rj.01",
        "profile_type": "EXECUTOR",
        "system": "SER",
        "state": "RJ",
        "state_name": "Rio de Janeiro",
    },
    {
        "username": "demo.ser.executor.rj.02",
        "profile_type": "EXECUTOR",
        "system": "SER",
        "state": "RJ",
        "state_name": "Rio de Janeiro",
    },
]

DEMO_PASSWORD = "demo_password_not_real"  # noqa: S105


async def seed() -> None:
    enabled = os.getenv("SEED_DEMO_CREDENTIALS", "").lower() == "true"
    if not enabled:
        logger.info("SEED_DEMO_CREDENTIALS not set to true, skipping demo credential seeding")
        return

    try:
        encrypted_password = encrypt_password(DEMO_PASSWORD)
    except Exception:
        logger.warning("Encryption key not configured, skipping demo credential seeding")
        return

    factory = get_session_factory()
    seeded = 0

    async with factory() as session:
        cred_repo = CredentialRepository(session)
        sys_repo = RegulationSystemRepository(session)

        # Resolve first active user as owner
        from sqlalchemy import select

        from regulahub.db.models import RegulaHubUser

        result = await session.execute(
            select(RegulaHubUser).where(RegulaHubUser.is_active.is_(True)).order_by(RegulaHubUser.created_at).limit(1)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("No active user found, skipping demo credential seeding")
            return

        for entry in DEMO_CREDENTIALS:
            profile_id = await sys_repo.resolve_profile_id(entry["system"], entry["profile_type"])
            if not profile_id:
                logger.warning("Cannot resolve profile for %s/%s, skipping", entry["system"], entry["profile_type"])
                continue

            existing = await cred_repo.get_by_user_profile_username(user.id, profile_id, entry["username"])
            if existing:
                continue

            await cred_repo.create(
                {
                    "user_id": user.id,
                    "profile_id": profile_id,
                    "username": entry["username"],
                    "encrypted_password": encrypted_password,
                    "state": entry["state"],
                    "state_name": entry["state_name"],
                    "unit_name": None,
                    "unit_cnes": None,
                }
            )
            seeded += 1
            logger.info("Seeded demo credential: %s (%s/%s)", entry["username"], entry["system"], entry["profile_type"])

        await session.commit()

    logger.info("Demo credential seeding complete: %d new credentials", seeded)


if __name__ == "__main__":
    asyncio.run(seed())
