"""Admin CRUD endpoints for credential management."""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.api.controllers.admin.schemas import (
    AdminCredentialCreate,
    AdminCredentialItem,
    AdminCredentialListResponse,
    AdminCredentialUpdate,
    AdminCredentialValidationItem,
    AdminProfileItem,
    AdminStateItem,
)
from regulahub.api.deps import verify_api_key
from regulahub.api.rate_limit import limiter
from regulahub.db.engine import get_session
from regulahub.db.models import System, SystemProfile, SystemType
from regulahub.db.repositories.credential import CredentialRepository
from regulahub.db.repositories.regulation_system import RegulationSystemRepository
from regulahub.utils.encryption import decrypt_password, encrypt_password
from regulahub.utils.masking import mask_username

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/credentials", tags=["admin-credentials"], dependencies=[Depends(verify_api_key)])


async def _batch_resolve_profiles(
    profile_ids: set[uuid.UUID], db: AsyncSession
) -> dict[uuid.UUID, tuple[str, str, str]]:
    """Batch-resolve (profile_name, system_code, scope) for a set of profile_ids."""
    if not profile_ids:
        return {}

    stmt = (
        select(SystemProfile, System.code, SystemType.code)
        .outerjoin(System, SystemProfile.system_id == System.id)
        .join(SystemType, SystemProfile.scope_id == SystemType.id)
        .where(SystemProfile.id.in_(profile_ids))
    )
    result = await db.execute(stmt)
    mapping: dict[uuid.UUID, tuple[str, str, str]] = {}
    for row in result.all():
        profile, system_code, scope_code = row
        mapping[profile.id] = (profile.profile_name, system_code or "", scope_code)
    return mapping


def _credential_to_item(cred, profile_name: str = "", system_code: str = "", scope: str = "") -> AdminCredentialItem:
    return AdminCredentialItem(
        id=cred.id,
        user_id=cred.user_id,
        profile_id=cred.profile_id,
        username=cred.username,
        profile_name=profile_name,
        system_code=system_code,
        scope=scope,
        state=cred.state,
        state_name=cred.state_name,
        unit_name=cred.unit_name,
        unit_cnes=cred.unit_cnes,
        is_active=cred.is_active,
        last_validated_at=cred.last_validated_at,
        is_valid=cred.is_valid,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
        created_by=cred.created_by,
        updated_by=cred.updated_by,
    )


async def _enrich_credentials(creds: list, db: AsyncSession) -> list[AdminCredentialItem]:
    """Resolve profile context for a list of credentials using batch load."""
    profile_ids = {cred.profile_id for cred in creds}
    profile_map = await _batch_resolve_profiles(profile_ids, db)
    items = []
    for cred in creds:
        pname, scode, scope = profile_map.get(cred.profile_id, ("", "", ""))
        items.append(_credential_to_item(cred, pname, scode, scope))
    return items


@router.get("", response_model=AdminCredentialListResponse)
@limiter.limit("30/minute")
async def list_credentials(
    request: Request,
    system: str | None = Query(None),
    profile_type: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
) -> AdminCredentialListResponse:
    repo = CredentialRepository(db)
    if user_id and system:
        creds = await repo.get_active_by_user_and_system(user_id, system)
    elif system and profile_type:
        creds = await repo.get_active_by_system_and_profile(system, profile_type)
    elif system:
        creds = await repo.get_active_by_system(system)
    else:
        creds = await repo.get_active_by_system("SISREG")
    total = len(creds)
    creds = creds[skip : skip + limit]
    items = await _enrich_credentials(creds, db)
    return AdminCredentialListResponse(items=items, total=total)


@router.post("", response_model=AdminCredentialItem, status_code=201)
@limiter.limit("10/minute")
async def create_credential(
    request: Request,
    body: AdminCredentialCreate,
    db: AsyncSession = Depends(get_session),
) -> AdminCredentialItem:
    sys_repo = RegulationSystemRepository(db)
    profile = await sys_repo.get_system_profile_by_id(body.profile_id)
    if not profile:
        raise HTTPException(status_code=400, detail=f"Unknown profile_id: {body.profile_id}")

    repo = CredentialRepository(db)
    existing = await repo.get_by_user_profile_username(body.user_id, body.profile_id, body.username)
    if existing:
        if not existing.is_active:
            reactivate_data = body.model_dump(exclude={"password"})
            reactivate_data["encrypted_password"] = encrypt_password(body.password)
            reactivate_data["is_active"] = True
            credential = await repo.update(existing.id, reactivate_data)
            await db.commit()
            profile_map = await _batch_resolve_profiles({credential.profile_id}, db)
            pname, scode, scope = profile_map.get(credential.profile_id, ("", "", ""))
            return _credential_to_item(credential, pname, scode, scope)
        raise HTTPException(status_code=409, detail="Credential already exists for this user/profile/username")

    data = body.model_dump(exclude={"password"})
    data["encrypted_password"] = encrypt_password(body.password)
    credential = await repo.create(data)
    await db.commit()
    profile_map = await _batch_resolve_profiles({credential.profile_id}, db)
    pname, scode, scope = profile_map.get(credential.profile_id, ("", "", ""))
    return _credential_to_item(credential, pname, scode, scope)


@router.put("/{credential_id}", response_model=AdminCredentialItem)
@limiter.limit("10/minute")
async def update_credential(
    request: Request,
    credential_id: uuid.UUID,
    body: AdminCredentialUpdate,
    db: AsyncSession = Depends(get_session),
) -> AdminCredentialItem:
    repo = CredentialRepository(db)
    update_data = body.model_dump(exclude_unset=True, exclude={"password"})
    if body.password is not None:
        update_data["encrypted_password"] = encrypt_password(body.password)
    credential = await repo.update(credential_id, update_data)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    await db.commit()
    profile_map = await _batch_resolve_profiles({credential.profile_id}, db)
    pname, scode, scope = profile_map.get(credential.profile_id, ("", "", ""))
    return _credential_to_item(credential, pname, scode, scope)


@router.delete("/{credential_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_credential(
    request: Request,
    credential_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    repo = CredentialRepository(db)
    success = await repo.deactivate(credential_id)
    if not success:
        raise HTTPException(status_code=404, detail="Credential not found")
    await db.commit()


@router.post("/validate-batch", response_model=list[AdminCredentialValidationItem])
@limiter.limit("5/minute")
async def validate_batch(
    request: Request,
    system: str = Query(...),
    profile_type: str = Query(...),
    db: AsyncSession = Depends(get_session),
) -> list[AdminCredentialValidationItem]:
    """Validate all credentials for a system/profile by testing decryption."""
    repo = CredentialRepository(db)
    creds = await repo.get_active_by_system_and_profile(system, profile_type)
    results: list[AdminCredentialValidationItem] = []
    now = datetime.now(UTC)
    for cred in creds:
        try:
            decrypt_password(cred.encrypted_password)
            await repo.update(cred.id, {"is_valid": True, "last_validated_at": now})
            results.append(AdminCredentialValidationItem(username=cred.username, valid=True))
        except Exception:
            logger.warning("Validation failed for credential %s", mask_username(cred.username))
            await repo.update(cred.id, {"is_valid": False, "last_validated_at": now})
            results.append(
                AdminCredentialValidationItem(username=cred.username, valid=False, error="Decryption failed")
            )
    await db.commit()
    return results


@router.get("/states", response_model=list[AdminStateItem])
@limiter.limit("30/minute")
async def list_states(
    request: Request,
    system: str = Query("SISREG"),
    db: AsyncSession = Depends(get_session),
) -> list[AdminStateItem]:
    repo = CredentialRepository(db)
    pairs = await repo.get_distinct_states(system)
    return [AdminStateItem(state=s, state_name=sn) for s, sn in pairs]


@router.get("/profiles", response_model=list[AdminProfileItem])
@limiter.limit("30/minute")
async def list_profiles(
    request: Request,
    system: str = Query("SISREG"),
    db: AsyncSession = Depends(get_session),
) -> list[AdminProfileItem]:
    cred_repo = CredentialRepository(db)
    distinct_profiles = await cred_repo.get_distinct_profiles(system)
    if distinct_profiles:
        return [AdminProfileItem(name=p, description="") for p in distinct_profiles]
    sys_repo = RegulationSystemRepository(db)
    profiles = await sys_repo.get_profiles_for_system(system)
    return [AdminProfileItem(name=p.profile_name, description=p.description or "") for p in profiles]
