"""Admin user registry — live platform accounts (admin API key required)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.services.admin_users_registry import build_admin_users_registry

router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_admin_api_key)],
)


class AdminUserSummaryOut(BaseModel):
    total: int
    active: int
    pending: int
    suspended: int
    leaders: int


class AdminUserOut(BaseModel):
    id: str
    full_name: str
    email: str
    mobile: str
    persona: str
    persona_label: str
    kyc_status: str
    status: str
    circle_id: Optional[str] = None
    circle_name: Optional[str] = None
    circle_role: Optional[str] = None
    is_circle_leader: bool = False
    zenq_score: Optional[int] = None
    inspire_index: Optional[float] = None
    zenq_contribution: Optional[float] = None
    group_contribution_inr: Optional[int] = None
    circle_spend_inr: Optional[int] = None
    circle_member_count: Optional[int] = None
    joined_at: Optional[str] = None
    last_active_at: Optional[str] = None


class AdminUsersRegistryOut(BaseModel):
    summary: AdminUserSummaryOut
    users: list[AdminUserOut]


@router.get("", response_model=AdminUsersRegistryOut)
async def list_admin_users(
    search: Optional[str] = Query(None, max_length=200),
    persona: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await build_admin_users_registry(
        db, search=search, persona=persona, status=status
    )
    return AdminUsersRegistryOut(**data)
