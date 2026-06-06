"""Live circle finance: budget figures and transactions from vendor orders."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.microservices.vendor.models import VendorOrder, VendorProduct
from app.models.signup import SignupRequest


def _fmt_date(dt: datetime | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%d %b")


def _category_for_order(order_type: str) -> str:
    if order_type == "student":
        return "Student"
    if order_type == "personal":
        return "Personal"
    return "Operational"


async def _circle_member_ids(db: AsyncSession, circle_id: str) -> list[str]:
    res = await db.execute(
        select(CircleMember.user_id).where(CircleMember.circle_id == circle_id)
    )
    return [r[0] for r in res.all()]


async def fetch_circle_orders(
    db: AsyncSession,
    circle: SponsorCircle,
) -> list[tuple[VendorOrder, Optional[str]]]:
    """Orders attributed to this circle (by circle_name or member buyer on student fund)."""
    member_ids = await _circle_member_ids(db, circle.id)
    clauses = []
    if circle.name:
        clauses.append(VendorOrder.circle_name == circle.name)
    if member_ids:
        clauses.append(
            (VendorOrder.buyer_id.in_(member_ids)) & (VendorOrder.order_type == "student")
        )
    if not clauses:
        return []
    q = (
        select(VendorOrder, VendorProduct.name)
        .outerjoin(VendorProduct, VendorProduct.id == VendorOrder.product_id)
        .where(or_(*clauses))
        .order_by(VendorOrder.created_at.desc())
    )
    res = await db.execute(q)
    return list(res.all())


def orders_to_budget_transactions(
    rows: list[tuple[VendorOrder, Optional[str]]],
) -> list[dict]:
    out: list[dict] = []
    for order, product_name in rows:
        amt = int(round(float(order.total_amount or 0)))
        desc = product_name or f"Order {str(order.id)[:8]}"
        if order.buyer_name:
            desc = f"{desc} — {order.buyer_name}"
        out.append(
            {
                "date": _fmt_date(order.created_at),
                "description": desc,
                "amount": amt,
                "category": _category_for_order(order.order_type or ""),
            }
        )
    return out


async def compute_spent_from_orders(db: AsyncSession, circle: SponsorCircle) -> int:
    rows = await fetch_circle_orders(db, circle)
    return sum(int(round(float(o.total_amount or 0))) for o, _ in rows)


def budget_numbers(circle: SponsorCircle, spent: int) -> dict[str, int]:
    total = int(circle.annual_budget or 0)
    collected = int(circle.budget_collected or 0)
    balance = max(0, total - spent) if total > 0 else 0
    return {
        "total_budget": total,
        "spent": spent,
        "collected": collected,
        "balance_to_spend": balance,
    }


async def build_statement(
    db: AsyncSession,
    circle: SponsorCircle,
) -> dict:
    rows = await fetch_circle_orders(db, circle)
    spent = sum(int(round(float(o.total_amount or 0))) for o, _ in rows)
    nums = budget_numbers(circle, spent)
    ledger: list[dict] = []
    running = nums["collected"]
    if nums["collected"] > 0:
        ledger.append(
            {
                "date": "",
                "type": "Opening",
                "tag": "opening",
                "desc": "Recorded collections (FY)",
                "debit": "—",
                "credit": f"₹{nums['collected']:,}",
                "balance": f"₹{running:,}",
            }
        )
    for order, product_name in sorted(rows, key=lambda r: r[0].created_at or datetime.min.replace(tzinfo=timezone.utc)):
        amt = int(round(float(order.total_amount or 0)))
        running = max(0, running - amt)
        ledger.append(
            {
                "date": _fmt_date(order.created_at),
                "type": _category_for_order(order.order_type or ""),
                "tag": "student" if order.order_type == "student" else "order",
                "desc": (product_name or "Marketplace order") + (f" — {order.buyer_name}" if order.buyer_name else ""),
                "debit": f"₹{amt:,}",
                "credit": "—",
                "balance": f"₹{running:,}",
            }
        )
    return {
        **nums,
        "fy_label": circle.fy_label or "2025-26",
        "circle_name": circle.name,
        "rows": ledger,
        "has_data": bool(ledger) or nums["total_budget"] > 0 or spent > 0,
    }


async def build_vendor_payments(
    db: AsyncSession,
    circle: SponsorCircle,
) -> list[dict]:
    rows = await fetch_circle_orders(db, circle)
    out = []
    for order, product_name in rows:
        status = order.status.value if hasattr(order.status, "value") else str(order.status)
        out.append(
            {
                "id": order.id,
                "date": _fmt_date(order.created_at),
                "vendor": product_name or "Vendor",
                "amount": int(round(float(order.total_amount or 0))),
                "status": status.replace("_", " ").title(),
                "category": _category_for_order(order.order_type or ""),
                "buyer_name": order.buyer_name,
            }
        )
    return out


async def build_member_contributions(
    db: AsyncSession,
    circle: SponsorCircle,
) -> dict:
    """Roster is live; per-member contribution amounts are not tracked in DB yet."""
    res = await db.execute(
        select(CircleMember, SignupRequest)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(CircleMember.circle_id == circle.id)
        .order_by(SignupRequest.full_name)
    )
    members = []
    for cm, signup in res.all():
        role = (cm.role or "sponsor").replace("_", " ")
        badge = ""
        if cm.role in ("lead", "sponsor_leader", "coordinator"):
            badge = "leader"
        members.append(
            {
                "name": signup.full_name,
                "initials": "".join(p[0] for p in (signup.full_name or "?").split()[:2]).upper(),
                "role": role,
                "total_contributed": None,
                "this_month": None,
                "pct": None,
                "badge": badge,
                "zenq": None,
            }
        )
    nums = budget_numbers(circle, await compute_spent_from_orders(db, circle))
    total_budget = nums["total_budget"]
    collected = nums["collected"]
    funded_pct = round((collected / total_budget) * 100) if total_budget > 0 else None
    return {
        "tracking_available": False,
        "members": members,
        "total_collected": collected if collected > 0 else None,
        "total_budget": total_budget if total_budget > 0 else None,
        "funded_pct": funded_pct,
        "spent": nums["spent"],
        "message": (
            "Per-member contribution tracking is not enabled yet. "
            "Fund totals below come from your circle budget and marketplace orders."
        ),
    }
