"""Platform analytics for admin dashboard — live aggregates and trends."""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.microservices.vendor.models import OrderStatus, VendorOrder, VendorProduct
from app.models.auth_log import AuthAuditLog
from app.models.enums import Persona
from app.models.school import SchoolStudent
from app.models.signup import SignupRequest
from app.services.admin_dashboard_overview import _month_start, _pct_change, _utc_now
from app.services.admin_financial_overview import _is_student_circle, _period_start, _previous_period_start

CHART_MONTHS = 6
SPONSOR_PERSONA_VALUES = frozenset(
    {
        Persona.sponsor.value,
        Persona.sponsor_leader.value,
        Persona.sponsor_member.value,
    }
)


def _in_range(dt: Optional[datetime], start: Optional[datetime], end: datetime) -> bool:
    if dt is None:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if start and dt < start:
        return False
    return dt <= end


def _last_month_buckets(count: int = CHART_MONTHS, now: Optional[datetime] = None) -> list[tuple[int, int, str]]:
    now = now or _utc_now()
    y, m = now.year, now.month
    buckets: list[tuple[int, int, str]] = []
    for offset in range(count - 1, -1, -1):
        mm = m - offset
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        buckets.append((yy, mm, calendar.month_abbr[mm]))
    return buckets


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


async def _distinct_success_logins(
    db: AsyncSession,
    *,
    since: datetime,
    until: datetime,
) -> int:
    res = await db.execute(
        select(func.count(func.distinct(AuthAuditLog.email))).where(
            AuthAuditLog.status == "SUCCESS",
            AuthAuditLog.timestamp >= since,
            AuthAuditLog.timestamp < until,
        )
    )
    return int(res.scalar_one() or 0)


async def build_admin_analytics_overview(
    db: AsyncSession,
    *,
    period: str = "month",
) -> dict[str, Any]:
    now = _utc_now()
    period = (period or "month").lower()
    start = _period_start(period, now)
    prev_start = _previous_period_start(period, now)
    prev_end = start

    # ── Users ─────────────────────────────────────────────────────────────
    users_res = await db.execute(select(SignupRequest))
    all_users = list(users_res.scalars().all())
    total_users = len(all_users)

    users_in_period = [u for u in all_users if _in_range(u.created_at, start, now)]
    users_prev = [
        u
        for u in all_users
        if prev_start
        and prev_end
        and _in_range(u.created_at, prev_start, prev_end)
    ]

    # ── Circles ───────────────────────────────────────────────────────────
    circles_res = await db.execute(select(SponsorCircle))
    all_circles = [c for c in circles_res.scalars().all() if _is_student_circle(c)]
    active_circles = [c for c in all_circles if (c.status or "active") == "active"]
    circles_in_period = [c for c in all_circles if _in_range(c.created_at, start, now)]
    circles_prev = [
        c
        for c in all_circles
        if prev_start and prev_end and _in_range(c.created_at, prev_start, prev_end)
    ]

    # ── Orders ────────────────────────────────────────────────────────────
    orders_res = await db.execute(
        select(VendorOrder).where(VendorOrder.status != OrderStatus.cancelled)
    )
    all_orders = list(orders_res.scalars().all())
    orders_in_period = [o for o in all_orders if _in_range(o.created_at, start, now)]
    orders_prev = [
        o
        for o in all_orders
        if prev_start and prev_end and _in_range(o.created_at, prev_start, prev_end)
    ]

    contrib_total = sum(int(c.budget_collected or 0) for c in all_circles)
    market_total = round(sum(float(o.total_amount or 0) for o in all_orders), 2)

    contrib_period = sum(
        int(c.budget_collected or 0)
        for c in all_circles
        if _in_range(c.budget_set_at or c.created_at, start, now)
    )
    market_period = round(sum(float(o.total_amount or 0) for o in orders_in_period), 2)
    revenue_period = contrib_period + market_period

    contrib_prev = sum(
        int(c.budget_collected or 0)
        for c in all_circles
        if prev_start
        and prev_end
        and _in_range(c.budget_set_at or c.created_at, prev_start, prev_end)
    )
    market_prev = round(sum(float(o.total_amount or 0) for o in orders_prev), 2)
    revenue_prev = contrib_prev + market_prev

    # ── Monthly chart series ──────────────────────────────────────────────
    month_buckets = _last_month_buckets(CHART_MONTHS, now)
    labels = [label for _, _, label in month_buckets]

    new_users_series: list[int] = []
    cumulative_users_series: list[int] = []
    marketplace_series: list[float] = []
    contributions_series: list[float] = []

    for year, month, _ in month_buckets:
        m_start, m_end = _month_bounds(year, month)
        new_users_series.append(
            sum(1 for u in all_users if _in_range(u.created_at, m_start, m_end))
        )
        cumulative_users_series.append(
            sum(1 for u in all_users if u.created_at and u.created_at < m_end)
        )
        marketplace_series.append(
            round(
                sum(
                    float(o.total_amount or 0)
                    for o in all_orders
                    if _in_range(o.created_at, m_start, m_end)
                ),
                2,
            )
        )
        contributions_series.append(
            float(
                sum(
                    int(c.budget_collected or 0)
                    for c in all_circles
                    if _in_range(c.budget_set_at or c.created_at, m_start, m_end)
                )
            )
        )

    # ── Persona distribution ────────────────────────────────────────────
    persona_counts: dict[str, int] = defaultdict(int)
    for u in all_users:
        p = u.persona.value if hasattr(u.persona, "value") else str(u.persona)
        if p in SPONSOR_PERSONA_VALUES or p.startswith("sponsor"):
            persona_counts["Sponsors"] += 1
        elif p == Persona.student.value:
            persona_counts["Students"] += 1
        elif p == Persona.vendor.value:
            persona_counts["Suppliers"] += 1
        elif p == Persona.school.value:
            persona_counts["Schools"] += 1
        elif p == Persona.mentor.value:
            persona_counts["Mentors"] += 1
        elif p == Persona.corporate.value:
            persona_counts["Corporate"] += 1
        else:
            persona_counts["Other"] += 1

    distribution_labels = [k for k, v in persona_counts.items() if v > 0]
    distribution_values = [persona_counts[k] for k in distribution_labels]

    # ── Engagement (successful logins) ──────────────────────────────────
    day_ago = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    month_ago = now - timedelta(days=30)
    two_months_ago = now - timedelta(days=60)

    dau = await _distinct_success_logins(db, since=day_ago, until=now)
    dau_prev = await _distinct_success_logins(db, since=two_days_ago, until=day_ago)
    wau = await _distinct_success_logins(db, since=week_ago, until=now)
    wau_prev = await _distinct_success_logins(db, since=two_weeks_ago, until=week_ago)
    mau = await _distinct_success_logins(db, since=month_ago, until=now)
    mau_prev = await _distinct_success_logins(db, since=two_months_ago, until=month_ago)

    # ── Top circles (school-linked students + ZenQ) ───────────────────────
    circle_stats_res = await db.execute(
        select(
            SchoolStudent.circle_id,
            func.count(SchoolStudent.id),
            func.avg(SchoolStudent.zqa_score),
        )
        .where(SchoolStudent.circle_id.isnot(None))
        .group_by(SchoolStudent.circle_id)
    )
    circle_name_map = {c.id: c.name for c in all_circles}
    top_circles: list[dict[str, Any]] = []
    for circle_id, student_count, avg_zqa in circle_stats_res.all():
        if circle_id not in circle_name_map:
            continue
        top_circles.append(
            {
                "name": circle_name_map[circle_id],
                "students": int(student_count or 0),
                "zenq_score": round(float(avg_zqa or 0), 1),
            }
        )
    top_circles.sort(key=lambda x: (x["zenq_score"], x["students"]), reverse=True)
    top_circles = top_circles[:5]

    if not top_circles:
        for c in sorted(active_circles, key=lambda x: int(x.budget_collected or 0), reverse=True)[:5]:
            top_circles.append(
                {
                    "name": c.name,
                    "students": 0,
                    "zenq_score": 0.0,
                    "collected": int(c.budget_collected or 0),
                }
            )

    # ── Top suppliers ─────────────────────────────────────────────────────
    vendor_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"orders": 0, "revenue": 0.0})
    for order in all_orders:
        vid = order.vendor_id
        if not vid:
            continue
        vendor_stats[vid]["orders"] += 1
        vendor_stats[vid]["revenue"] += float(order.total_amount or 0)

    vendor_ids = list(vendor_stats.keys())
    vendor_names: dict[str, str] = {}
    if vendor_ids:
        v_res = await db.execute(select(SignupRequest).where(SignupRequest.id.in_(vendor_ids)))
        for v in v_res.scalars().all():
            vendor_names[v.id] = (
                v.company_name or v.business_name or v.full_name or v.email or "Vendor"
            )

    top_suppliers = [
        {
            "name": vendor_names.get(vid, "Vendor"),
            "orders": stats["orders"],
            "revenue": round(stats["revenue"], 2),
        }
        for vid, stats in vendor_stats.items()
    ]
    top_suppliers.sort(key=lambda x: x["revenue"], reverse=True)
    top_suppliers = top_suppliers[:5]

    # ── Operations snapshot (real queues, not fake uptime) ────────────────
    from app.chat.models import SOSReport
    from app.models.circle_ops import CircleAdminRequest, STATUS_PENDING
    from app.models.enums import KycStatus

    kyc_pending_res = await db.execute(
        select(func.count())
        .select_from(SignupRequest)
        .where(SignupRequest.kyc_status == KycStatus.pending)
    )
    sos_open_res = await db.execute(
        select(func.count()).select_from(SOSReport).where(SOSReport.resolved_at.is_(None))
    )
    ops_pending_res = await db.execute(
        select(func.count())
        .select_from(CircleAdminRequest)
        .where(CircleAdminRequest.status == STATUS_PENDING)
    )
    pending_orders = sum(1 for o in all_orders if o.status == OrderStatus.pending)

    kyc_pending = int(kyc_pending_res.scalar_one() or 0)
    sos_open = int(sos_open_res.scalar_one() or 0)
    ops_pending = int(ops_pending_res.scalar_one() or 0)

    return {
        "generated_at": now.isoformat(),
        "period": period,
        "currency": "INR",
        "kpis": {
            "total_users": total_users,
            "users_in_period": len(users_in_period),
            "users_change_pct": _pct_change(len(users_in_period), len(users_prev)),
            "active_circles": len(active_circles),
            "circles_in_period": len(circles_in_period),
            "circles_change": len(circles_in_period) - len(circles_prev),
            "marketplace_orders": len(orders_in_period) if start else len(all_orders),
            "orders_in_period": len(orders_in_period),
            "orders_change_pct": _pct_change(len(orders_in_period), len(orders_prev)),
            "total_revenue": round(contrib_total + market_total, 2),
            "revenue_in_period": round(revenue_period, 2),
            "revenue_change_pct": _pct_change(int(revenue_period), int(revenue_prev)),
            "marketplace_gmv_total": market_total,
            "contributions_total": contrib_total,
        },
        "charts": {
            "labels": labels,
            "user_growth": {
                "new_users": new_users_series,
                "cumulative_users": cumulative_users_series,
            },
            "revenue_trend": {
                "marketplace": marketplace_series,
                "contributions": contributions_series,
            },
            "user_distribution": {
                "labels": distribution_labels,
                "values": distribution_values,
            },
        },
        "engagement": {
            "daily_active_logins": dau,
            "daily_change_pct": _pct_change(dau, dau_prev),
            "weekly_active_logins": wau,
            "weekly_change_pct": _pct_change(wau, wau_prev),
            "monthly_active_logins": mau,
            "monthly_change_pct": _pct_change(mau, mau_prev),
        },
        "top_circles": top_circles,
        "top_suppliers": top_suppliers,
        "operations": {
            "kyc_pending": kyc_pending,
            "sos_open": sos_open,
            "circle_ops_pending": ops_pending,
            "pending_marketplace_orders": pending_orders,
            "all_clear": kyc_pending == 0 and sos_open == 0 and ops_pending == 0,
        },
    }
