"""Admin CRUD endpoints for RegulaHub users and their selections."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.api.controllers.admin.schemas import (
    AdminUpsertSelectionRequest,
    AdminUserItem,
    AdminUserListResponse,
    AdminUserSelectionItem,
    AdminUserSelectionListResponse,
)
from regulahub.api.deps import verify_api_key
from regulahub.api.rate_limit import limiter
from regulahub.db.engine import get_session
from regulahub.db.repositories.user import UserRepository

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=AdminUserListResponse)
@limiter.limit("30/minute")
async def list_users(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
) -> AdminUserListResponse:
    repo = UserRepository(db)
    users = await repo.list_active()
    total = len(users)
    users = users[skip : skip + limit]
    return AdminUserListResponse(
        items=[AdminUserItem.model_validate(u) for u in users],
        total=total,
    )


@router.get("/{user_id}/selections", response_model=AdminUserSelectionListResponse)
@limiter.limit("30/minute")
async def get_user_selections(
    request: Request,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> AdminUserSelectionListResponse:
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    selections = await repo.get_selections_for_user(user_id)
    return AdminUserSelectionListResponse(
        items=[AdminUserSelectionItem.model_validate(s) for s in selections],
        total=len(selections),
    )


@router.put("/{user_id}/selections", response_model=AdminUserSelectionItem)
@limiter.limit("10/minute")
async def upsert_user_selection(
    request: Request,
    user_id: uuid.UUID,
    body: AdminUpsertSelectionRequest,
    db: AsyncSession = Depends(get_session),
) -> AdminUserSelectionItem:
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    selection = await repo.upsert_selection(
        user_id=user_id,
        system=body.system,
        profile_type=body.profile_type,
        state=body.state,
        state_name=body.state_name,
        selected_users=body.selected_users,
    )
    await db.commit()
    return AdminUserSelectionItem.model_validate(selection)


@router.delete("/{user_id}/selections/{system}/{profile_type}", status_code=204)
@limiter.limit("10/minute")
async def delete_user_selection(
    request: Request,
    user_id: uuid.UUID,
    system: str,
    profile_type: str,
    db: AsyncSession = Depends(get_session),
) -> None:
    repo = UserRepository(db)
    success = await repo.delete_selection(user_id, system, profile_type)
    if not success:
        raise HTTPException(status_code=404, detail="Selection not found")
    await db.commit()
