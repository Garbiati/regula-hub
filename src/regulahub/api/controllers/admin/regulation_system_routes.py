"""Admin CRUD endpoints for regulation systems, profiles, and form metadata."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.api.controllers.admin.schemas import (
    AdminRegulationSystemCreate,
    AdminRegulationSystemItem,
    AdminRegulationSystemListResponse,
    AdminRegulationSystemUpdate,
    AdminSystemProfileCreate,
    AdminSystemProfileItem,
    AdminSystemProfileListResponse,
    AdminSystemProfileUpdate,
    FormMetadataResponse,
    FormMetadataUpdate,
)
from regulahub.api.deps import verify_api_key
from regulahub.api.rate_limit import limiter
from regulahub.db.engine import get_session
from regulahub.db.repositories.regulation_system import RegulationSystemRepository
from regulahub.services.form_metadata import get_form_metadata, update_form_metadata

router = APIRouter(
    prefix="/api/admin/regulation-systems",
    tags=["admin-regulation-systems"],
    dependencies=[Depends(verify_api_key)],
)


# ── Systems ──────────────────────────────────────────────────────────


@router.get("", response_model=AdminRegulationSystemListResponse)
@limiter.limit("30/minute")
async def list_systems(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
) -> AdminRegulationSystemListResponse:
    repo = RegulationSystemRepository(db)
    items = await repo.list_active()
    total = len(items)
    items = items[skip : skip + limit]
    return AdminRegulationSystemListResponse(
        items=[AdminRegulationSystemItem.model_validate(s) for s in items],
        total=total,
    )


@router.get("/{system_id}", response_model=AdminRegulationSystemItem)
@limiter.limit("30/minute")
async def get_system(
    request: Request,
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> AdminRegulationSystemItem:
    repo = RegulationSystemRepository(db)
    system = await repo.get_by_id(system_id)
    if not system:
        raise HTTPException(status_code=404, detail="Regulation system not found")
    return AdminRegulationSystemItem.model_validate(system)


@router.post("", response_model=AdminRegulationSystemItem, status_code=201)
@limiter.limit("10/minute")
async def create_system(
    request: Request,
    body: AdminRegulationSystemCreate,
    db: AsyncSession = Depends(get_session),
) -> AdminRegulationSystemItem:
    repo = RegulationSystemRepository(db)
    existing = await repo.get_by_code(body.code)
    if existing:
        raise HTTPException(status_code=409, detail="System code already exists")
    system = await repo.create(body.model_dump())
    await db.commit()
    return AdminRegulationSystemItem.model_validate(system)


@router.put("/{system_id}", response_model=AdminRegulationSystemItem)
@limiter.limit("10/minute")
async def update_system(
    request: Request,
    system_id: uuid.UUID,
    body: AdminRegulationSystemUpdate,
    db: AsyncSession = Depends(get_session),
) -> AdminRegulationSystemItem:
    repo = RegulationSystemRepository(db)
    system = await repo.update(system_id, body.model_dump(exclude_unset=True))
    if not system:
        raise HTTPException(status_code=404, detail="Regulation system not found")
    await db.commit()
    return AdminRegulationSystemItem.model_validate(system)


@router.delete("/{system_id}", status_code=204)
@limiter.limit("10/minute")
async def deactivate_system(
    request: Request,
    system_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    repo = RegulationSystemRepository(db)
    success = await repo.deactivate(system_id)
    if not success:
        raise HTTPException(status_code=404, detail="Regulation system not found")
    await db.commit()


# ── Profiles ─────────────────────────────────────────────────────────


def _profile_to_item(profile, system_code: str, scope: str = "regulation") -> AdminSystemProfileItem:
    return AdminSystemProfileItem(
        id=profile.id,
        scope=scope,
        system_id=profile.system_id,
        system_code=system_code,
        profile_name=profile.profile_name,
        description=profile.description,
        level=profile.level,
        sort_order=profile.sort_order,
        is_active=profile.is_active,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        created_by=profile.created_by,
        updated_by=profile.updated_by,
    )


@router.get("/{code}/profiles", response_model=AdminSystemProfileListResponse)
@limiter.limit("30/minute")
async def list_profiles(
    request: Request,
    code: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
) -> AdminSystemProfileListResponse:
    repo = RegulationSystemRepository(db)
    items = await repo.get_profiles_for_system(code)
    total = len(items)
    items = items[skip : skip + limit]
    return AdminSystemProfileListResponse(
        items=[_profile_to_item(p, code) for p in items],
        total=total,
    )


@router.post("/{code}/profiles", response_model=AdminSystemProfileItem, status_code=201)
@limiter.limit("10/minute")
async def create_profile(
    request: Request,
    code: str,
    body: AdminSystemProfileCreate,
    db: AsyncSession = Depends(get_session),
) -> AdminSystemProfileItem:
    repo = RegulationSystemRepository(db)
    system = await repo.get_by_code(code)
    if not system or not system.is_active:
        raise HTTPException(status_code=404, detail="Regulation system not found")
    data = body.model_dump()
    data["scope"] = "regulation"
    data["system_id"] = system.id
    profile = await repo.create_profile(data)
    await db.commit()
    return _profile_to_item(profile, code)


@router.put("/profiles/{profile_id}", response_model=AdminSystemProfileItem)
@limiter.limit("10/minute")
async def update_profile(
    request: Request,
    profile_id: uuid.UUID,
    body: AdminSystemProfileUpdate,
    db: AsyncSession = Depends(get_session),
) -> AdminSystemProfileItem:
    repo = RegulationSystemRepository(db)
    profile = await repo.update_profile(profile_id, body.model_dump(exclude_unset=True))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.commit()
    # Resolve system_code for response
    system_code = ""
    if profile.system_id:
        system = await repo.get_by_id(profile.system_id)
        system_code = system.code if system else ""
    return _profile_to_item(profile, system_code)


@router.delete("/profiles/{profile_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_profile(
    request: Request,
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    repo = RegulationSystemRepository(db)
    success = await repo.delete_profile(profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.commit()


# ── Form Metadata ───────────────────────────────────────────────────


@router.get("/{code}/form-metadata/{endpoint_name}")
@limiter.limit("60/minute")
async def get_endpoint_form_metadata(
    request: Request,
    code: str,
    endpoint_name: str,
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    data, etag = await get_form_metadata(db, code, endpoint_name)
    if data is None:
        raise HTTPException(status_code=404, detail="Form metadata not found for this system/endpoint")

    # Support conditional requests
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match and etag and if_none_match.strip('"') == etag:
        return JSONResponse(status_code=304, content=None)

    validated = FormMetadataResponse(**data)
    return JSONResponse(
        content=validated.model_dump(exclude_none=True),
        headers={
            "Cache-Control": "public, max-age=300",
            "ETag": f'"{etag}"',
        },
    )


@router.put("/{code}/form-metadata/{endpoint_name}", response_model=FormMetadataResponse)
@limiter.limit("10/minute")
async def put_endpoint_form_metadata(
    request: Request,
    code: str,
    endpoint_name: str,
    body: FormMetadataUpdate,
    db: AsyncSession = Depends(get_session),
) -> FormMetadataResponse:
    update_dict = body.model_dump(exclude_none=True)
    # Convert nested Pydantic models to dicts for merge
    for field in ("search_types", "situations", "items_per_page"):
        items = getattr(body, field, None)
        if field in update_dict and items is not None:
            update_dict[field] = [s.model_dump(exclude_none=True) for s in items]
    if "defaults" in update_dict and body.defaults is not None:
        update_dict["defaults"] = body.defaults.model_dump()

    result = await update_form_metadata(db, code, endpoint_name, update_dict)
    if result is None:
        raise HTTPException(status_code=404, detail="System or endpoint not found")
    await db.commit()
    return FormMetadataResponse(**result)
