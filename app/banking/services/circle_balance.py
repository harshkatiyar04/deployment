"""
Live circle money snapshot for banking (ICICI in + out).

Collected ledger: SponsorCircle.budget_collected (incremented by eCollection credits).
VAN credited: sum of credited eCollection transactions (ICICI money-in source of truth).
Spendable: collected − marketplace order spend − paid disbursements − in-flight processing.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking.models.icici_ecollection import TXN_CREDITED, EcollectionTransaction
from app.chat.models import SponsorCircle
from app.models.circle_ops import (
    DISBURSEMENT_PAID,
    DISBURSEMENT_PENDING,
    DISBURSEMENT_PROCESSING,
    CircleDisbursement,
)
from app.services.sponsor_circle_finance import fetch_circle_orders


async def sum_van_credited_inr(db: AsyncSession, circle_id: str) -> int:
    res = await db.execute(
        select(func.coalesce(func.sum(EcollectionTransaction.amount_paise), 0)).where(
            EcollectionTransaction.circle_id == circle_id,
            EcollectionTransaction.status == TXN_CREDITED,
        )
    )
    paise = int(res.scalar_one() or 0)
    return int(paise // 100)


async def sum_disbursements_inr(
    db: AsyncSession,
    circle_id: str,
    *,
    statuses: tuple[str, ...],
) -> int:
    res = await db.execute(
        select(func.coalesce(func.sum(CircleDisbursement.amount_inr), 0)).where(
            CircleDisbursement.circle_id == circle_id,
            CircleDisbursement.status.in_(list(statuses)),
        )
    )
    return int(res.scalar_one() or 0)


async def build_live_money_snapshot(
    db: AsyncSession,
    circle: SponsorCircle,
) -> dict[str, Any]:
    """Fresh numbers for banking UI + disbursement gates."""
    await db.refresh(circle)

    rows = await fetch_circle_orders(db, circle)
    order_spent = sum(int(round(float(o.total_amount or 0))) for o, _ in rows)
    paid_out = await sum_disbursements_inr(
        db, circle.id, statuses=(DISBURSEMENT_PAID,)
    )
    reserved = await sum_disbursements_inr(
        db,
        circle.id,
        statuses=(DISBURSEMENT_PROCESSING, DISBURSEMENT_PENDING),
    )
    van_credited = await sum_van_credited_inr(db, circle.id)

    collected = int(circle.budget_collected or 0)
    # Display collected prefers ledger; VAN total is the ICICI live feed
    spent = order_spent + paid_out
    available = max(0, collected - spent - reserved)

    return {
        "collected": collected,
        "van_credited": van_credited,
        "spent": spent,
        "order_spent": order_spent,
        "disbursed_paid": paid_out,
        "reserved_in_flight": reserved,
        "available": available,
        "fy_label": circle.fy_label,
        "live": True,
    }


def format_insufficient_balance(available: int, amount: int) -> str:
    return (
        f"Insufficient balance. Available ₹{available:,}; "
        f"this payment needs ₹{amount:,}."
    )
