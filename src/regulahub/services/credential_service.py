"""Centralized credential resolution — DB lookup + decryption."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.utils.masking import mask_username

logger = logging.getLogger(__name__)


class CredentialNotFoundError(Exception):
    """No active credentials found or all failed decryption."""


async def resolve_single_credential(
    system: str,
    profile_type: str,
    *,
    db_session: AsyncSession | None = None,
) -> tuple[str, str]:
    """Resolve a single credential (username, password) from the DB.

    If db_session is None, creates its own session via get_session_factory().
    Raises CredentialNotFoundError on failure.
    """
    from regulahub.db.repositories.credential import CredentialRepository

    if db_session is not None:
        return await _resolve_first(CredentialRepository(db_session), system, profile_type)

    from regulahub.db.engine import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        return await _resolve_first(CredentialRepository(session), system, profile_type)


async def resolve_credential_by_cnes(
    system: str,
    profile_type: str,
    unit_cnes: str,
    *,
    db_session: AsyncSession,
) -> tuple[str, str]:
    """Resolve a credential for a specific unit CNES.

    Raises CredentialNotFoundError if no matching credential is found.
    """
    from regulahub.db.repositories.credential import CredentialRepository
    from regulahub.utils.encryption import decrypt_password

    repo = CredentialRepository(db_session)
    creds = await repo.get_active_by_system_and_profile(system, profile_type)
    for cred in creds:
        if cred.unit_cnes == unit_cnes:
            try:
                return cred.username, decrypt_password(cred.encrypted_password)
            except ValueError:
                logger.warning("Failed to decrypt password for credential %s", mask_username(cred.username))
                raise CredentialNotFoundError(f"Decryption failed for CNES {unit_cnes}") from None
    raise CredentialNotFoundError(f"No operator found for CNES {unit_cnes}")


async def resolve_credential_by_username(
    system: str,
    profile_type: str,
    username: str,
    *,
    db_session: AsyncSession,
) -> tuple[str, str]:
    """Resolve a credential for a specific username.

    Raises CredentialNotFoundError if no matching credential is found.
    """
    from regulahub.db.repositories.credential import CredentialRepository
    from regulahub.utils.encryption import decrypt_password

    repo = CredentialRepository(db_session)
    creds = await repo.get_active_by_system_and_profile(system, profile_type)
    for cred in creds:
        if cred.username == username:
            try:
                return cred.username, decrypt_password(cred.encrypted_password)
            except ValueError:
                logger.warning("Failed to decrypt password for credential %s", mask_username(cred.username))
                raise CredentialNotFoundError(f"Decryption failed for username {username}") from None
    raise CredentialNotFoundError(f"No credential found for username {username}")


async def resolve_credentials_for_cnes_set(
    system: str,
    profile_type: str,
    requested_cnes: set[str],
    *,
    db_session: AsyncSession,
) -> list[tuple[str, str, str, str]]:
    """Resolve credentials for multiple unit CNES codes.

    Returns list of (username, password, unit_name, unit_cnes) for each matched CNES.
    Skips individual decryption failures with a warning.
    Raises CredentialNotFoundError if no credentials could be resolved.
    """
    from regulahub.db.repositories.credential import CredentialRepository
    from regulahub.utils.encryption import decrypt_password

    repo = CredentialRepository(db_session)
    db_creds = await repo.get_active_by_system_and_profile(system, profile_type)

    selected: list[tuple[str, str, str, str]] = []
    for cred in db_creds:
        if cred.unit_cnes in requested_cnes:
            try:
                pw = decrypt_password(cred.encrypted_password)
                selected.append((cred.username, pw, cred.unit_name or "", cred.unit_cnes or ""))
            except ValueError:
                logger.warning("Failed to decrypt password for credential %s", mask_username(cred.username))

    if not selected:
        raise CredentialNotFoundError("No matching operators found for the given CNES codes")
    return selected


async def _resolve_first(
    repo,
    system: str,
    profile_type: str,
) -> tuple[str, str]:
    """Resolve the first valid credential from the repository."""
    from regulahub.utils.encryption import decrypt_password

    creds = await repo.get_active_by_system_and_profile(system, profile_type)
    if not creds:
        raise CredentialNotFoundError(f"No {profile_type} credentials configured for {system}")

    try:
        return creds[0].username, decrypt_password(creds[0].encrypted_password)
    except ValueError:
        user_hash = mask_username(creds[0].username)
        logger.warning("Failed to decrypt %s credential (user=%s) from DB", profile_type, user_hash)
        raise CredentialNotFoundError(f"Failed to decrypt {profile_type} credential") from None
