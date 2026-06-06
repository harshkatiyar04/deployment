"""Unified admin dashboard overview (admin API key required)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.services.admin_dashboard_overview import build_admin_dashboard_overview

router = APIRouter(
    prefix="/admin/overview",
    tags=["admin-overview"],
    dependencies=[Depends(require_admin_api_key)],
)


class AdminKpisOut(BaseModel):
    total_users: int
    users_change_pct: Optional[float] = None
    users_new_this_month: int = 0
    active_circles: int
    circle_members: int = 0
    circles_change: int = 0
    circles_new_this_month: int = 0
    circle_hours_month: float = 0
    suppliers_total: int
    suppliers_approved: int = 0
    suppliers_new_this_month: int = 0
    active_products: int = 0
    marketplace_gmv: float
    delivered_gmv: float = 0
    gmv_mtd: float = 0
    total_contributions: int
    circle_spend_total: int = 0


class AdminQueuesOut(BaseModel):
    kyc_pending: int
    circle_ops_pending: int
    uplift_pending: int
    sos_open: int
    chat_warned: int
    chat_bans: int
    safety_pending: int


class AdminSafetyOut(BaseModel):
    content_review_pending: int
    sos_open: int
    all_clear: bool


class AdminActivityItem(BaseModel):
    type: str
    action: str
    subject: str
    at: Optional[str] = None


class AdminDashboardOverviewOut(BaseModel):
    generated_at: Optional[str] = None
    kpis: AdminKpisOut
    queues: AdminQueuesOut
    safety: AdminSafetyOut
    recent_activity: list[AdminActivityItem] = Field(default_factory=list)


@router.get("", response_model=AdminDashboardOverviewOut)
async def get_admin_dashboard_overview(db: AsyncSession = Depends(get_db)):
    data: dict[str, Any] = await build_admin_dashboard_overview(db)
    return AdminDashboardOverviewOut(**data)
