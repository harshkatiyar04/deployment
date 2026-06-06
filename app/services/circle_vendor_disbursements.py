"""Circle vendor payees and ICICI disbursement flow."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.core.settings import settings
from app.models.circle_ops import (
    DISBURSEMENT_PAID,
    DISBURSEMENT_PENDING,
    DISBURSEMENT_PROCESSING,
    PAYEE_CATEGORIES,
    CircleDisbursement,
    CirclePayee,
)
from app.models.signup import SignupRequest


def _fmt_date(dt: datetime | date | None) -> str:
    if not dt:
        return ""
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.strftime("%d %b")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%d %b")


def _mask_account(account: str) -> str:
    raw = (account or "").strip()
    if len(raw) <= 4:
        return "****"
    return f"****{raw[-4:]}"


def _category_label(cat: str) -> str:
    labels = {
        "school_fees": "School Fees",
        "supplies": "Supplies",
        "books": "Books",
        "uniform": "Uniform",
        "other": "Other",
    }
    return labels.get((cat or "").lower(), "Other")


def payee_to_dict(payee: CirclePayee) -> dict[str, Any]:
    return {
        "id": payee.id,
        "display_name": payee.display_name,
        "beneficiary_name": payee.beneficiary_name,
        "category": payee.category,
        "category_label": _category_label(payee.category),
        "bank_name": payee.bank_name,
        "account_masked": _mask_account(payee.account_number),
        "ifsc": payee.ifsc,
        "upi_id": payee.upi_id,
        "notes": payee.notes,
        "is_active": payee.is_active,
        "created_at": payee.created_at.isoformat() if payee.created_at else None,
    }


def disbursement_to_dict(
    row: CircleDisbursement,
    *,
    payee: Optional[CirclePayee] = None,
) -> dict[str, Any]:
    vendor = payee.display_name if payee else "Payee"
    return {
        "id": row.id,
        "date": _fmt_date(row.paid_at or row.created_at),
        "vendor": vendor,
        "description": row.description,
        "amount": row.amount_inr,
        "status": (row.status or "pending").title(),
        "status_key": (row.status or "pending").lower(),
        "category": _category_label(row.category),
        "category_key": row.category,
        "payee_id": row.payee_id,
        "due_date": row.due_date.isoformat() if row.due_date else None,
        "due_date_label": _fmt_date(row.due_date) if row.due_date else None,
        "gateway_ref": row.gateway_ref,
        "paid_at": row.paid_at.isoformat() if row.paid_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def list_circle_payees(db: AsyncSession, circle_id: str) -> list[dict[str, Any]]:
    res = await db.execute(
        select(CirclePayee)
        .where(CirclePayee.circle_id == circle_id, CirclePayee.is_active.is_(True))
        .order_by(CirclePayee.display_name)
    )
    return [payee_to_dict(p) for p in res.scalars().all()]


async def create_circle_payee(
    db: AsyncSession,
    *,
    circle_id: str,
    created_by: str,
    display_name: str,
    beneficiary_name: str,
    category: str,
    account_number: str,
    ifsc: str,
    bank_name: Optional[str] = None,
    upi_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    cat = (category or "other").lower()
    if cat not in PAYEE_CATEGORIES:
        raise ValueError("Invalid payee category")

    payee = CirclePayee(
        circle_id=circle_id,
        display_name=display_name.strip(),
        beneficiary_name=beneficiary_name.strip(),
        category=cat,
        bank_name=(bank_name or "").strip() or None,
        account_number=account_number.strip(),
        ifsc=ifsc.strip().upper(),
        upi_id=(upi_id or "").strip() or None,
        notes=(notes or "").strip() or None,
        created_by=created_by,
    )
    db.add(payee)
    await db.flush()
    return payee_to_dict(payee)


def _build_icici_redirect_url(
    *,
    session_id: str,
    amount_inr: int,
    payee_name: str,
    disbursement_id: str,
    circle_id: str,
) -> str:
    base = (settings.icici_gateway_base_url or "").strip().rstrip("/")
    frontend = (settings.frontend_base_url or settings.website_url or "http://localhost:5173").rstrip("/")
    return_url = (
        f"{frontend}/payments/icici/return"
        f"?session={session_id}&disbursement={disbursement_id}&circle={circle_id}"
    )

    if base:
        params = {
            "mid": settings.icici_merchant_id or "",
            "txnId": session_id,
            "amount": str(amount_inr),
            "payee": payee_name[:80],
            "returnUrl": return_url,
        }
        return f"{base}?{urlencode(params)}"

    # Dev / staging: internal checkout hands off to return URL after leader confirms
    return f"{frontend}/payments/icici/checkout?{urlencode({
        'session': session_id,
        'disbursement': disbursement_id,
        'amount': amount_inr,
        'circle': circle_id,
    })}"


async def initiate_disbursement(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    user: SignupRequest,
    payee_id: str,
    amount_inr: int,
    description: str,
    due_date: Optional[date] = None,
) -> dict[str, Any]:
    if amount_inr < 1:
        raise ValueError("Amount must be at least ₹1")
    if amount_inr > 5_000_000:
        raise ValueError("Amount exceeds per-transaction limit")

    p_res = await db.execute(
        select(CirclePayee).where(
            CirclePayee.id == payee_id,
            CirclePayee.circle_id == circle.id,
            CirclePayee.is_active.is_(True),
        )
    )
    payee = p_res.scalar_one_or_none()
    if not payee:
        raise ValueError("Payee not found for this circle")

    session_id = secrets.token_hex(16)
    desc = (description or "").strip() or f"Payment to {payee.display_name}"

    row = CircleDisbursement(
        circle_id=circle.id,
        payee_id=payee.id,
        amount_inr=amount_inr,
        description=desc[:300],
        category=payee.category,
        status=DISBURSEMENT_PROCESSING,
        due_date=due_date,
        gateway_provider="icici",
        gateway_session_id=session_id,
        created_by=user.id,
    )
    db.add(row)
    await db.flush()

    redirect_url = _build_icici_redirect_url(
        session_id=session_id,
        amount_inr=amount_inr,
        payee_name=payee.beneficiary_name,
        disbursement_id=row.id,
        circle_id=circle.id,
    )
    return {
        "disbursement_id": row.id,
        "session_id": session_id,
        "redirect_url": redirect_url,
        "amount_inr": amount_inr,
        "payee_name": payee.display_name,
    }


async def complete_disbursement(
    db: AsyncSession,
    *,
    circle_id: str,
    disbursement_id: str,
    session_id: str,
    success: bool,
    gateway_ref: Optional[str] = None,
) -> dict[str, Any]:
    res = await db.execute(
        select(CircleDisbursement, CirclePayee)
        .join(CirclePayee, CirclePayee.id == CircleDisbursement.payee_id)
        .where(
            CircleDisbursement.id == disbursement_id,
            CircleDisbursement.circle_id == circle_id,
            CircleDisbursement.gateway_session_id == session_id,
        )
    )
    row = res.first()
    if not row:
        raise ValueError("Payment session not found")

    disbursement, payee = row
    if disbursement.status == DISBURSEMENT_PAID:
        return disbursement_to_dict(disbursement, payee=payee)

    now = datetime.now(timezone.utc)
    if success:
        disbursement.status = DISBURSEMENT_PAID
        disbursement.paid_at = now
        disbursement.gateway_ref = (gateway_ref or "").strip() or f"ICICI-{session_id[:12].upper()}"
    else:
        disbursement.status = DISBURSEMENT_PENDING

    await db.flush()
    return disbursement_to_dict(disbursement, payee=payee)


async def build_vendor_payments_dashboard(
    db: AsyncSession,
    circle: SponsorCircle,
) -> dict[str, Any]:
    d_res = await db.execute(
        select(CircleDisbursement, CirclePayee)
        .join(CirclePayee, CirclePayee.id == CircleDisbursement.payee_id)
        .where(CircleDisbursement.circle_id == circle.id)
        .order_by(CircleDisbursement.created_at.desc())
    )
    rows = d_res.all()
    history = [disbursement_to_dict(d, payee=p) for d, p in rows]

    total_disbursed = sum(
        d.amount_inr for d, _ in rows if (d.status or "").lower() == DISBURSEMENT_PAID
    )
    total_pending = sum(
        d.amount_inr
        for d, _ in rows
        if (d.status or "").lower() in (DISBURSEMENT_PENDING, DISBURSEMENT_PROCESSING)
    )
    payee_res = await db.execute(
        select(func.count())
        .select_from(CirclePayee)
        .where(CirclePayee.circle_id == circle.id, CirclePayee.is_active.is_(True))
    )
    vendors_served = int(payee_res.scalar_one() or 0)

    next_pending = None
    for d, p in rows:
        if (d.status or "").lower() in (DISBURSEMENT_PENDING, DISBURSEMENT_PROCESSING):
            next_pending = {
                "id": d.id,
                "amount": d.amount_inr,
                "description": d.description,
                "due_date_label": _fmt_date(d.due_date) if d.due_date else None,
                "payee_name": p.display_name,
            }
            break

    payees = await list_circle_payees(db, circle.id)

    return {
        "total_disbursed": total_disbursed,
        "total_pending": total_pending,
        "vendors_served": vendors_served,
        "payment_history": history,
        "payees": payees,
        "next_deposit_request": next_pending,
        "gateway_provider": "ICICI Bank",
    }
