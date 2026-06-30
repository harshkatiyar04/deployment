"""Unified admin dashboard overview (admin API key required)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.core.rate_limit import limiter
from app.db.resilience import safe_service_unavailable_detail, with_db_retry
from app.db.session import SessionLocal, get_db
from app.services.admin_analytics_overview import build_admin_analytics_overview
from app.services.admin_dashboard_overview import build_admin_dashboard_overview
from app.services.admin_financial_overview import build_admin_financial_overview
from app.services.admin_overview_cache import (
    build_and_cache_dashboard_overview,
    get_cached_dashboard_overview,
)

logger = logging.getLogger(__name__)

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
    other_requests_pending: int = 0
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


async def _build_dashboard_overview(session: AsyncSession) -> dict[str, Any]:
    return await build_and_cache_dashboard_overview(
        session,
        build_admin_dashboard_overview,
    )


async def _run_with_db_retry(build_fn) -> dict[str, Any]:
    """Retry once with a fresh session when the pool hands back a dead connection."""

    async def _once() -> dict[str, Any]:
        async with SessionLocal() as db:
            return await build_fn(db)

    return await with_db_retry(_once)


@router.get("", response_model=AdminDashboardOverviewOut)
@limiter.limit("30/minute")
async def get_admin_dashboard_overview(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    cached = get_cached_dashboard_overview()
    if cached is not None:
        return AdminDashboardOverviewOut(**cached)

    try:
        data = await _build_dashboard_overview(db)
        return AdminDashboardOverviewOut(**data)
    except HTTPException:
        raise
    except Exception:
        try:
            data = await _run_with_db_retry(_build_dashboard_overview)
            return AdminDashboardOverviewOut(**data)
        except HTTPException:
            raise
        except Exception:
            logger.exception("admin_dashboard_overview_failed")
            raise HTTPException(
                status_code=503,
                detail=safe_service_unavailable_detail(),
            ) from None


class AdminFinancialSummaryOut(BaseModel):
    total_contributions: float
    total_marketplace_gmv: float
    platform_commission: float
    pending_amount: float
    pending_count: int
    completed_count: int
    completed_amount: float
    contributions_change_pct: Optional[float] = None
    marketplace_change_pct: Optional[float] = None
    commission_change_pct: Optional[float] = None
    revenue_breakdown: dict[str, Any]
    status_breakdown: dict[str, Any]


class AdminFinancialTransactionOut(BaseModel):
    id: str
    type: str
    type_label: str
    amount: float
    commission: float
    from_label: str
    to_label: str
    status: str
    date: Optional[str] = None
    occurred_at: Optional[str] = None


class AdminFinancialOverviewOut(BaseModel):
    generated_at: Optional[str] = None
    period: str
    txn_type: str
    currency: str = "INR"
    commission_rate_pct: float = 5.0
    summary: AdminFinancialSummaryOut
    transactions: list[AdminFinancialTransactionOut] = Field(default_factory=list)


@router.get("/financial", response_model=AdminFinancialOverviewOut)
@limiter.limit("30/minute")
async def get_admin_financial_overview(
    request: Request,
    period: str = "month",
    txn_type: str = "all",
):
    try:
        data = await _run_with_db_retry(
            lambda db: build_admin_financial_overview(db, period=period, txn_type=txn_type),
        )
        return AdminFinancialOverviewOut(**data)
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin_financial_overview_failed")
        raise HTTPException(
            status_code=503,
            detail=safe_service_unavailable_detail(),
        ) from None


class AdminAnalyticsKpisOut(BaseModel):
    total_users: int
    users_in_period: int = 0
    users_change_pct: Optional[float] = None
    active_circles: int
    circles_in_period: int = 0
    circles_change: int = 0
    marketplace_orders: int
    orders_in_period: int = 0
    orders_change_pct: Optional[float] = None
    total_revenue: float
    revenue_in_period: float = 0
    revenue_change_pct: Optional[float] = None
    marketplace_gmv_total: float = 0
    contributions_total: int = 0


class AdminAnalyticsOverviewOut(BaseModel):
    generated_at: Optional[str] = None
    period: str
    currency: str = "INR"
    kpis: AdminAnalyticsKpisOut
    charts: dict[str, Any]
    engagement: dict[str, Any]
    top_circles: list[dict[str, Any]] = Field(default_factory=list)
    top_suppliers: list[dict[str, Any]] = Field(default_factory=list)
    operations: dict[str, Any] = Field(default_factory=dict)


@router.get("/analytics", response_model=AdminAnalyticsOverviewOut)
@limiter.limit("30/minute")
async def get_admin_analytics_overview(
    request: Request,
    period: str = "month",
):
    try:
        payload = await _run_with_db_retry(
            lambda db: build_admin_analytics_overview(db, period=period),
        )
        return AdminAnalyticsOverviewOut(**payload)
    except HTTPException:
        raise
    except Exception:
        logger.exception("admin_analytics_overview_failed")
        raise HTTPException(
            status_code=503,
            detail=safe_service_unavailable_detail(),
        ) from None
