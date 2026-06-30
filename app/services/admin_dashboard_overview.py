"""Platform-wide metrics for the admin dashboard (single secured aggregator)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatBan, ChatMessage, SOSReport, SponsorCircle
from app.microservices.vendor.models import OrderStatus, VendorOrder, VendorProduct
from app.models.circle_ops import CircleAdminRequest, STATUS_PENDING
from app.models.enums import KycStatus, Persona
from app.models.mentor import MentorUpliftAction
from app.models.signup import SignupRequest
from app.services.admin_circle_overview import admin_circles_summary_light

DELIVERED_STATUSES = (
    OrderStatus.delivered,
    OrderStatus.shipped,
    OrderStatus.processing,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.isoformat()


def _month_start(now: Optional[datetime] = None) -> datetime:
    now = now or _utc_now()
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def _pct_change(current: int, previous: int) -> Optional[float]:
    if previous <= 0:
        return None if current <= 0 else 100.0
    return round(100.0 * (current - previous) / previous, 1)


async def _count_signups_between(
    db: AsyncSession, start: datetime, end: Optional[datetime] = None
) -> int:
    q = select(func.count()).select_from(SignupRequest).where(SignupRequest.created_at >= start)
    if end is not None:
        q = q.where(SignupRequest.created_at < end)
    res = await db.execute(q)
    return int(res.scalar_one() or 0)


async def _count_circles_since(db: AsyncSession, since: datetime) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(SponsorCircle)
        .where(SponsorCircle.created_at >= since)
    )
    return int(res.scalar_one() or 0)


async def build_admin_dashboard_overview(db: AsyncSession) -> dict[str, Any]:
    now = _utc_now()
    this_month = _month_start(now)
    last_month_end = this_month
    last_month_start = datetime(
        last_month_end.year if last_month_end.month > 1 else last_month_end.year - 1,
        last_month_end.month - 1 if last_month_end.month > 1 else 12,
        1,
        tzinfo=timezone.utc,
    )

    # ── Users / KYC ───────────────────────────────────────────────────────
    users_total_res = await db.execute(select(func.count()).select_from(SignupRequest))
    users_total = int(users_total_res.scalar_one() or 0)

    kyc_pending_res = await db.execute(
        select(func.count())
        .select_from(SignupRequest)
        .where(SignupRequest.kyc_status == KycStatus.pending)
    )
    kyc_pending = int(kyc_pending_res.scalar_one() or 0)

    users_this_month = await _count_signups_between(db, this_month)
    users_last_month = await _count_signups_between(db, last_month_start, this_month)

    # ── Circles ───────────────────────────────────────────────────────────
    circle_summary = await admin_circles_summary_light(db)
    circles_this_month = await _count_circles_since(db, this_month)
    circles_last_month_res = await db.execute(
        select(func.count())
        .select_from(SponsorCircle)
        .where(
            SponsorCircle.created_at >= last_month_start,
            SponsorCircle.created_at < this_month,
        )
    )
    circles_last_month = int(circles_last_month_res.scalar_one() or 0)

    # ── Vendors / suppliers ─────────────────────────────────────────────────
    vendors_res = await db.execute(
        select(func.count())
        .select_from(SignupRequest)
        .where(SignupRequest.persona == Persona.vendor)
    )
    vendors_total = int(vendors_res.scalar_one() or 0)

    vendors_approved_res = await db.execute(
        select(func.count())
        .select_from(SignupRequest)
        .where(
            SignupRequest.persona == Persona.vendor,
            SignupRequest.kyc_status == KycStatus.approved,
        )
    )
    vendors_approved = int(vendors_approved_res.scalar_one() or 0)

    products_res = await db.execute(
        select(func.count())
        .select_from(VendorProduct)
        .where(VendorProduct.is_active.is_(True))
    )
    active_products = int(products_res.scalar_one() or 0)

    vendors_this_month_res = await db.execute(
        select(func.count())
        .select_from(SignupRequest)
        .where(
            SignupRequest.persona == Persona.vendor,
            SignupRequest.created_at >= this_month,
        )
    )
    vendors_this_month = int(vendors_this_month_res.scalar_one() or 0)

    # ── Orders / financial ────────────────────────────────────────────────
    gmv_res = await db.execute(
        select(func.coalesce(func.sum(VendorOrder.total_amount), 0)).where(
            VendorOrder.status != OrderStatus.cancelled
        )
    )
    marketplace_gmv = float(gmv_res.scalar_one() or 0)

    delivered_gmv_res = await db.execute(
        select(func.coalesce(func.sum(VendorOrder.total_amount), 0)).where(
            VendorOrder.status.in_(list(DELIVERED_STATUSES))
        )
    )
    delivered_gmv = float(delivered_gmv_res.scalar_one() or 0)

    budget_collected_res = await db.execute(
        select(func.coalesce(func.sum(SponsorCircle.budget_collected), 0))
    )
    total_contributions = int(budget_collected_res.scalar_one() or 0)

    budget_spent_res = await db.execute(
        select(func.coalesce(func.sum(SponsorCircle.budget_spent), 0))
    )
    circle_spend_total = int(budget_spent_res.scalar_one() or 0)

    orders_mtd_res = await db.execute(
        select(func.coalesce(func.sum(VendorOrder.total_amount), 0)).where(
            VendorOrder.created_at >= this_month,
            VendorOrder.status != OrderStatus.cancelled,
        )
    )
    gmv_mtd = float(orders_mtd_res.scalar_one() or 0)

    # ── Safety / queues ───────────────────────────────────────────────────
    sos_open_res = await db.execute(
        select(func.count()).select_from(SOSReport).where(SOSReport.resolved_at.is_(None))
    )
    sos_open = int(sos_open_res.scalar_one() or 0)

    chat_warn_res = await db.execute(
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.shield_action == "warn", ChatMessage.hidden_at.is_(None))
    )
    chat_warned = int(chat_warn_res.scalar_one() or 0)

    chat_bans_res = await db.execute(select(func.count()).select_from(ChatBan))
    chat_bans = int(chat_bans_res.scalar_one() or 0)

    circle_ops_res = await db.execute(
        select(func.count())
        .select_from(CircleAdminRequest)
        .where(
            CircleAdminRequest.status == STATUS_PENDING,
            CircleAdminRequest.request_type.in_(["member_removal", "member_limit_increase"]),
        )
    )
    circle_ops_pending = int(circle_ops_res.scalar_one() or 0)

    other_requests_res = await db.execute(
        select(func.count())
        .select_from(CircleAdminRequest)
        .where(
            CircleAdminRequest.status == STATUS_PENDING,
            CircleAdminRequest.request_type.in_(["circle_rename"]),
        )
    )
    other_requests_pending = int(other_requests_res.scalar_one() or 0)

    uplift_pending_res = await db.execute(
        select(func.count())
        .select_from(MentorUpliftAction)
        .where(MentorUpliftAction.verified.is_(False))
    )
    uplift_pending = int(uplift_pending_res.scalar_one() or 0)

    safety_pending = sos_open + chat_warned

    # ── Recent activity feed ────────────────────────────────────────────────
    recent: list[dict[str, Any]] = []

    signup_rows = await db.execute(
        select(SignupRequest)
        .order_by(SignupRequest.created_at.desc())
        .limit(6)
    )
    for s in signup_rows.scalars().all():
        persona = s.persona.value if hasattr(s.persona, "value") else str(s.persona)
        recent.append(
            {
                "type": "signup",
                "action": f"New {persona.replace('_', ' ')} registered",
                "subject": s.full_name or s.email,
                "at": _iso(s.created_at),
            }
        )

    circle_rows = await db.execute(
        select(SponsorCircle).order_by(SponsorCircle.created_at.desc()).limit(4)
    )
    for c in circle_rows.scalars().all():
        recent.append(
            {
                "type": "circle",
                "action": "Circle created",
                "subject": c.name,
                "at": _iso(c.created_at),
            }
        )

    order_rows = await db.execute(
        select(VendorOrder).order_by(VendorOrder.created_at.desc()).limit(4)
    )
    for o in order_rows.scalars().all():
        recent.append(
            {
                "type": "order",
                "action": f"Marketplace order ({o.status.value if hasattr(o.status, 'value') else o.status})",
                "subject": o.circle_name or o.buyer_name,
                "at": _iso(o.created_at),
            }
        )

    recent.sort(key=lambda x: x.get("at") or "", reverse=True)
    recent = recent[:10]

    return {
        "generated_at": _iso(now),
        "kpis": {
            "total_users": users_total,
            "users_change_pct": _pct_change(users_this_month, users_last_month),
            "users_new_this_month": users_this_month,
            "active_circles": circle_summary["total_circles"],
            "circle_members": circle_summary["total_members"],
            "circles_change": circles_this_month - circles_last_month,
            "circles_new_this_month": circles_this_month,
            "circle_hours_month": circle_summary["total_hours_month"],
            "suppliers_total": vendors_total,
            "suppliers_approved": vendors_approved,
            "suppliers_new_this_month": vendors_this_month,
            "active_products": active_products,
            "marketplace_gmv": round(marketplace_gmv, 2),
            "delivered_gmv": round(delivered_gmv, 2),
            "gmv_mtd": round(gmv_mtd, 2),
            "total_contributions": total_contributions,
            "circle_spend_total": circle_spend_total,
        },
        "queues": {
            "kyc_pending": kyc_pending,
            "circle_ops_pending": circle_ops_pending,
            "other_requests_pending": other_requests_pending,
            "uplift_pending": uplift_pending,
            "sos_open": sos_open,
            "chat_warned": chat_warned,
            "chat_bans": chat_bans,
            "safety_pending": safety_pending,
        },
        "safety": {
            "content_review_pending": chat_warned,
            "sos_open": sos_open,
            "all_clear": safety_pending == 0,
        },
        "recent_activity": recent,
    }
