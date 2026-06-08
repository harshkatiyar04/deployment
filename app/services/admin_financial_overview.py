"""Admin financial oversight — live ledger from circles, orders, and disbursements."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.microservices.vendor.models import OrderStatus, VendorOrder, VendorProduct
from app.models.circle_ops import DISBURSEMENT_PAID, DISBURSEMENT_PENDING, CircleDisbursement
from app.models.signup import SignupRequest
from app.services.admin_dashboard_overview import _month_start, _pct_change, _utc_now
from app.services.school_circle_sync import resolve_circle_leader_signup

PLATFORM_COMMISSION_RATE = 0.05
CORPORATE_KIA_CIRCLE_PREFIX = "Corporate Kia -"
CORPORATE_KIA_CIRCLE_DESC = "Private corporate Kia channel"

COMPLETED_ORDER_STATUSES = frozenset(
    {OrderStatus.delivered, OrderStatus.shipped, OrderStatus.processing}
)


def _is_student_circle(circle: SponsorCircle) -> bool:
    if (circle.description or "").strip() == CORPORATE_KIA_CIRCLE_DESC:
        return False
    if (circle.name or "").startswith(CORPORATE_KIA_CIRCLE_PREFIX):
        return False
    return True


def _period_start(period: str, now: Optional[datetime] = None) -> Optional[datetime]:
    now = now or _utc_now()
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return _month_start(now)
    if period == "quarter":
        q_month = ((now.month - 1) // 3) * 3 + 1
        return datetime(now.year, q_month, 1, tzinfo=timezone.utc)
    if period == "year":
        return datetime(now.year, 1, 1, tzinfo=timezone.utc)
    return None


def _previous_period_start(period: str, now: Optional[datetime] = None) -> Optional[datetime]:
    now = now or _utc_now()
    if period == "week":
        return now - timedelta(days=14)
    if period == "month":
        cur = _month_start(now)
        if cur.month == 1:
            return datetime(cur.year - 1, 12, 1, tzinfo=timezone.utc)
        return datetime(cur.year, cur.month - 1, 1, tzinfo=timezone.utc)
    if period == "quarter":
        cur = _period_start("quarter", now)
        if not cur:
            return None
        if cur.month <= 3:
            return datetime(cur.year - 1, 10, 1, tzinfo=timezone.utc)
        return datetime(cur.year, cur.month - 3, 1, tzinfo=timezone.utc)
    if period == "year":
        return datetime(now.year - 1, 1, 1, tzinfo=timezone.utc)
    return None


def _in_range(dt: Optional[datetime], start: Optional[datetime], end: datetime) -> bool:
    if dt is None:
        return start is None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if start and dt < start:
        return False
    return dt <= end


def _commission(amount: float, *, earned: bool) -> float:
    if not earned:
        return 0.0
    return round(float(amount) * PLATFORM_COMMISSION_RATE, 2)


def _summarize_transactions(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [t for t in transactions if t["status"] == "completed"]
    pending = [t for t in transactions if t["status"] == "pending"]

    contrib_completed = [t for t in completed if t["type"] == "contribution"]
    market_completed = [t for t in completed if t["type"] == "marketplace"]

    total_contributions = round(sum(t["amount"] for t in contrib_completed), 2)
    total_marketplace = round(sum(t["amount"] for t in market_completed), 2)
    total_commission = round(sum(t["commission"] for t in completed), 2)
    pending_amount = round(sum(t["amount"] for t in pending), 2)

    revenue_total = total_contributions + total_marketplace
    contrib_pct = round(100.0 * total_contributions / revenue_total, 1) if revenue_total > 0 else 0.0
    market_pct = round(100.0 * total_marketplace / revenue_total, 1) if revenue_total > 0 else 0.0

    completed_amount = round(sum(t["amount"] for t in completed), 2)

    return {
        "total_contributions": total_contributions,
        "total_marketplace_gmv": total_marketplace,
        "platform_commission": total_commission,
        "pending_amount": pending_amount,
        "pending_count": len(pending),
        "completed_count": len(completed),
        "completed_amount": completed_amount,
        "revenue_breakdown": {
            "contributions": total_contributions,
            "contributions_pct": contrib_pct,
            "marketplace": total_marketplace,
            "marketplace_pct": market_pct,
        },
        "status_breakdown": {
            "completed_count": len(completed),
            "completed_amount": completed_amount,
            "pending_count": len(pending),
            "pending_amount": pending_amount,
        },
    }


async def build_admin_financial_overview(
    db: AsyncSession,
    *,
    period: str = "month",
    txn_type: str = "all",
) -> dict[str, Any]:
    now = _utc_now()
    period = (period or "month").lower()
    txn_type = (txn_type or "all").lower()
    start = _period_start(period, now)
    prev_start = _previous_period_start(period, now)

    transactions: list[dict[str, Any]] = []

    # ── Circle contribution aggregates (budget_collected) ─────────────────
    circles_res = await db.execute(select(SponsorCircle).order_by(SponsorCircle.name))
    for circle in circles_res.scalars().all():
        if not _is_student_circle(circle):
            continue
        collected = int(circle.budget_collected or 0)
        if collected <= 0:
            continue
        leader = await resolve_circle_leader_signup(db, circle.id)
        leader_name = (leader.full_name or leader.email or "Circle leader") if leader else "Circle leader"
        event_at = circle.budget_set_at or circle.created_at
        transactions.append(
            {
                "id": f"contrib-{circle.id}",
                "type": "contribution",
                "type_label": "Contribution",
                "amount": float(collected),
                "commission": _commission(collected, earned=True),
                "from_label": leader_name,
                "to_label": circle.name,
                "status": "completed",
                "date": event_at.date().isoformat() if event_at else None,
                "occurred_at": event_at.isoformat() if event_at else None,
            }
        )

    # ── Circle vendor disbursements ───────────────────────────────────────
    disb_res = await db.execute(
        select(CircleDisbursement, SponsorCircle)
        .join(SponsorCircle, SponsorCircle.id == CircleDisbursement.circle_id)
        .order_by(CircleDisbursement.created_at.desc())
    )
    for disb, circle in disb_res.all():
        if not _is_student_circle(circle):
            continue
        status = "completed" if disb.status == DISBURSEMENT_PAID else "pending"
        event_at = disb.paid_at or disb.created_at
        transactions.append(
            {
                "id": f"disb-{disb.id}",
                "type": "disbursement",
                "type_label": "Circle disbursement",
                "amount": float(disb.amount_inr or 0),
                "commission": 0.0,
                "from_label": circle.name,
                "to_label": disb.description or "Vendor payee",
                "status": status,
                "date": event_at.date().isoformat() if event_at else None,
                "occurred_at": event_at.isoformat() if event_at else None,
            }
        )

    # ── Marketplace orders ────────────────────────────────────────────────
    orders_res = await db.execute(
        select(VendorOrder, VendorProduct, SignupRequest)
        .outerjoin(VendorProduct, VendorProduct.id == VendorOrder.product_id)
        .outerjoin(SignupRequest, SignupRequest.id == VendorOrder.vendor_id)
        .where(VendorOrder.status != OrderStatus.cancelled)
        .order_by(VendorOrder.created_at.desc())
    )
    for order, product, vendor in orders_res.all():
        st = order.status
        status = "pending" if st == OrderStatus.pending else "completed"
        earned = st in COMPLETED_ORDER_STATUSES
        vendor_label = (
            (vendor.company_name or vendor.business_name or vendor.full_name)
            if vendor
            else "Marketplace vendor"
        )
        product_label = product.name if product else vendor_label
        transactions.append(
            {
                "id": f"order-{order.id}",
                "type": "marketplace",
                "type_label": "Marketplace purchase",
                "amount": round(float(order.total_amount or 0), 2),
                "commission": _commission(order.total_amount or 0, earned=earned),
                "from_label": order.buyer_name or "Buyer",
                "to_label": product_label or vendor_label,
                "status": status,
                "date": order.created_at.date().isoformat() if order.created_at else None,
                "occurred_at": order.created_at.isoformat() if order.created_at else None,
            }
        )

    transactions.sort(key=lambda t: t.get("occurred_at") or "", reverse=True)

    def _filter_period(rows: list[dict[str, Any]], p_start: Optional[datetime]) -> list[dict[str, Any]]:
        return [
            t
            for t in rows
            if _in_range(
                datetime.fromisoformat(t["occurred_at"]) if t.get("occurred_at") else None,
                p_start,
                now,
            )
        ]

    def _filter_type(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if txn_type == "all":
            return rows
        if txn_type == "contribution":
            return [t for t in rows if t["type"] == "contribution"]
        if txn_type == "marketplace":
            return [t for t in rows if t["type"] == "marketplace"]
        if txn_type == "disbursement":
            return [t for t in rows if t["type"] == "disbursement"]
        return rows

    period_rows = _filter_period(transactions, start)
    period_rows = _filter_type(period_rows)

    prev_end = start
    prev_rows = _filter_period(transactions, prev_start)
    if prev_start and prev_end:
        prev_rows = [
            t
            for t in prev_rows
            if _in_range(
                datetime.fromisoformat(t["occurred_at"]) if t.get("occurred_at") else None,
                prev_start,
                prev_end,
            )
        ]
    prev_rows = _filter_type(prev_rows)

    summary = _summarize_transactions(period_rows)
    prev_summary = _summarize_transactions(prev_rows)

    return {
        "generated_at": now.isoformat(),
        "period": period,
        "txn_type": txn_type,
        "currency": "INR",
        "commission_rate_pct": round(PLATFORM_COMMISSION_RATE * 100, 1),
        "summary": {
            **summary,
            "contributions_change_pct": _pct_change(
                int(summary["total_contributions"]),
                int(prev_summary["total_contributions"]),
            ),
            "marketplace_change_pct": _pct_change(
                int(summary["total_marketplace_gmv"]),
                int(prev_summary["total_marketplace_gmv"]),
            ),
            "commission_change_pct": _pct_change(
                int(summary["platform_commission"]),
                int(prev_summary["platform_commission"]),
            ),
        },
        "transactions": period_rows,
    }
