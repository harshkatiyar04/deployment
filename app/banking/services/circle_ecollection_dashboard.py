

from __future__ import annotations

import logging
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.core.settings import settings
from app.banking.models.icici_ecollection import (
    TXN_CREDITED,
    EcollectionTransaction,
    EcollectionVan,
)
from app.banking.services import icici_ecollection as eco

logger = logging.getLogger(__name__)

# Soft in-process throttle for simulate (per leader)
_SIM_LAST: dict[str, float] = {}
_SIM_MIN_INTERVAL_SEC = 3.0


def _client_code() -> str:
    code = (settings.icici_ecollection_client_code or "ZENK01").strip().upper()
    code = re.sub(r"[^A-Z0-9]", "", code)[:6]
    return (code or "ZENK01").ljust(6, "0")[:6]


def _circle_suffix(circle_id: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]", "", circle_id or "")[:10].upper()
    return compact or "CIRCLE"


def simulate_enabled() -> bool:
    """
    Mock bank credit is OFF in production-like hosts unless explicitly enabled.
    Local / explicit UAT can turn it on.
    """
    if settings.icici_ecollection_simulate_enabled is True:
        return True
    if settings.icici_ecollection_simulate_enabled is False:
        return False
    # Auto: allow only when plaintext mock mode is on and not on Railway
    import os

    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
        return False
    return bool(settings.icici_ecollection_plaintext)


async def ensure_circle_van(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
) -> EcollectionVan:
    client_code = _client_code()
    suffix = _circle_suffix(circle.id)
    van = eco.build_van(client_code, suffix)

    res = await db.execute(
        select(EcollectionVan).where(
            EcollectionVan.circle_id == circle.id,
            EcollectionVan.is_active.is_(True),
        )
    )
    existing = res.scalars().first()
    if existing:
        return existing

    # Collision-safe: if VAN taken by another circle, append short entropy
    clash = await db.execute(select(EcollectionVan).where(EcollectionVan.van == van))
    if clash.scalar_one_or_none():
        suffix = f"{suffix}{secrets.token_hex(2).upper()}"[:24]
        van = eco.build_van(client_code, suffix)

    return await eco.register_van(
        db,
        client_code=client_code,
        suffix=suffix,
        circle_id=circle.id,
        purpose="Circle contributions (eCollection)",
    )


async def list_circle_credits(
    db: AsyncSession,
    *,
    circle_id: str,
    limit: int = 25,
) -> list[dict[str, Any]]:
    lim = max(1, min(int(limit or 25), 50))
    res = await db.execute(
        select(EcollectionTransaction)
        .where(EcollectionTransaction.circle_id == circle_id)
        .order_by(desc(EcollectionTransaction.created_at))
        .limit(lim)
    )
    rows = res.scalars().all()
    out = []
    for t in rows:
        out.append(
            {
                "id": t.id,
                "utr": t.utr,
                "amount_inr": t.amount_inr,
                "amount_paise": t.amount_paise,
                "status": t.status,
                "payment_mode": t.payment_mode,
                "remitter_name": t.remitter_name,
                "van": t.van,
                "bank_tran_date": t.bank_tran_date,
                "ledger_posted": t.ledger_posted,
                "credited_at": t.credited_at.isoformat() if t.credited_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
        )
    return out


async def build_collections_dashboard(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
) -> dict[str, Any]:
    van_row = await ensure_circle_van(db, circle=circle)
    credits = await list_circle_credits(db, circle_id=circle.id)
    credited = [c for c in credits if c["status"] == TXN_CREDITED]
    total_credited = sum(int(c["amount_paise"]) for c in credited) / 100.0
    return {
        "van": van_row.van,
        "client_code": van_row.client_code,
        "van_purpose": van_row.purpose,
        "ifsc_hint": "ICIC000XXXX (as issued by ICICI for eCollection)",
        "beneficiary_name": "ZenK Impact Collections",
        "simulate_enabled": simulate_enabled(),
        "total_credited_inr": round(total_credited, 2),
        "credit_count": len(credited),
        "recent_credits": credits,
        "allowed_payment_modes": [
            {"code": "NEFT", "label": "NEFT"},
            {"code": "RTGS", "label": "RTGS"},
            {"code": "IMPS", "label": "IMPS"},
            {"code": "UPI", "label": "UPI"},
            {"code": "FT", "label": "Fund transfer"},
        ],
        "security": {
            "webhook_auth": "basic_auth_optional",
            "idempotency": "utr_plus_amount",
            "deemed_action": "reject",
            "encryption": "pending_bank_sample",
        },
    }


def _throttle_simulate(user_id: str) -> None:
    now = time.monotonic()
    last = _SIM_LAST.get(user_id, 0.0)
    if now - last < _SIM_MIN_INTERVAL_SEC:
        raise ValueError("Please wait a few seconds before simulating another credit.")
    _SIM_LAST[user_id] = now


ALLOWED_SIM_MODES = frozenset({"NEFT", "RTGS", "IMPS", "UPI", "FT"})


async def simulate_bank_credit(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    user_id: str,
    amount_inr: str = "100.00",
    remitter_name: str = "Demo Remitter",
    payment_mode: str = "NEFT",
) -> dict[str, Any]:
    if not simulate_enabled():
        raise PermissionError("Bank credit simulation is disabled in this environment.")

    _throttle_simulate(user_id)

    mode_raw = (payment_mode or "NEFT").strip().upper()
    if mode_raw not in ALLOWED_SIM_MODES:
        raise ValueError("Payment mode must be NEFT, RTGS, IMPS, UPI, or FT")

    # Cap mock amounts — never allow huge ledger swings from the demo button
    display, paise = eco.normalize_amount_to_paise(amount_inr)
    if paise > 100_000_00:  # ₹1,00,000
        raise ValueError("Simulate amount cannot exceed ₹1,00,000")
    if paise < 100:  # ₹1
        raise ValueError("Simulate amount must be at least ₹1")

    van_row = await ensure_circle_van(db, circle=circle)
    utr = (
        f"MOCK{mode_raw[:4]}"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        f"{secrets.token_hex(2).upper()}"
    )
    payload = {
        "CUSTOMER CODE": van_row.client_code,
        "VIRTUAL ACCOUNT NUMBER": van_row.van,
        "TRANSACTION AMOUNT": display,
        "CURRENCY CODE": "INR",
        "PAYMENT MODE": mode_raw,
        "UTR": utr,
        "DATE": datetime.now(timezone.utc).strftime("%d-%m-%Y"),
        "SENDER NAME": (remitter_name or "Demo Remitter")[:30],
        "SENDER ACCOUNT NUMBER": "0000000000",
        "SENDER IFSC": "ICIC0000001",
    }

    # Run through the same handlers the bank will call
    v_resp, _ = await eco.handle_validation(db, payload, client_ip="127.0.0.1")
    if v_resp.get("STATUS") != "A":
        return {
            "ok": False,
            "stage": "validate",
            "utr": utr,
            "payment_mode": mode_raw,
            "response": v_resp,
        }

    confirm_payload = {
        "CUSTOMER_CODE": van_row.client_code,
        "VAN": van_row.van,
        "AMOUNT": display,
        "CURRENCY_CODE": "INR",
        "PAYMENT_MODE": mode_raw,
        "UTR": utr,
        "TRAN_DATE": payload["DATE"],
        "REMITTERNAME": payload["SENDER NAME"],
        "REMITTER_ACCNO": "0000000000",
        "REMITTER_IFSC": "ICIC0000001",
    }
    c_resp, _ = await eco.handle_credit_confirm(db, confirm_payload, client_ip="127.0.0.1")
    return {
        "ok": c_resp.get("STATUS") == "A",
        "stage": "credit_confirm",
        "utr": utr,
        "amount_inr": display,
        "van": van_row.van,
        "payment_mode": mode_raw,
        "validate": v_resp,
        "confirm": c_resp,
    }


def _member_safe_credit_row(t: EcollectionTransaction) -> dict[str, Any]:
    """Own-credit projection — no peer remitter leakage beyond the caller's match."""
    return {
        "id": t.id,
        "utr": (t.utr or "")[:16],
        "amount_inr": t.amount_inr,
        "amount_paise": t.amount_paise,
        "status": t.status,
        "payment_mode": t.payment_mode,
        "credited_at": t.credited_at.isoformat() if t.credited_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


async def build_member_contribute(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    user: Any,
) -> dict[str, Any]:
    """
    Member pay-in view: circle VAN + credits attributed to this user's KYC name only.
    Never returns other members' remitter lines.
    """
    from app.services.sponsor_circle_finance import (
        _match_remitter_to_member,
        fetch_credited_ecollection,
    )

    van_row = await ensure_circle_van(db, circle=circle)
    kyc_name = (getattr(user, "full_name", None) or "").strip()
    credits = await fetch_credited_ecollection(db, circle.id)
    me_bucket = [{"match_name": kyc_name, "name": kyc_name}]

    my_total = 0
    my_this_month = 0
    my_credits: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    circle_collected = sum(int(t.amount_paise or 0) // 100 for t in credits)

    for txn in credits:
        if not _match_remitter_to_member(txn.remitter_name, me_bucket):
            continue
        amt = int(txn.amount_paise or 0) // 100
        my_total += amt
        when = txn.credited_at or txn.created_at
        if when and when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when and when.year == now.year and when.month == now.month:
            my_this_month += amt
        my_credits.append(_member_safe_credit_row(txn))

    my_credits.reverse()  # newest first for UI

    if kyc_name:
        message = (
            f"Pay to the circle VAN using your bank app. Remitter name must match your KYC name "
            f"“{kyc_name}” so the credit attributes to you."
        )
    else:
        message = (
            "Pay to the circle VAN using your bank app. Use your legal KYC full name as remitter."
        )

    return {
        "van": van_row.van,
        "client_code": van_row.client_code,
        "van_purpose": van_row.purpose,
        "ifsc_hint": "ICIC000XXXX (as issued by ICICI for eCollection)",
        "beneficiary_name": "ZenK Impact Collections",
        "allowed_payment_modes": [
            {"code": "NEFT", "label": "NEFT"},
            {"code": "RTGS", "label": "RTGS"},
            {"code": "IMPS", "label": "IMPS"},
            {"code": "UPI", "label": "UPI"},
            {"code": "FT", "label": "Fund transfer"},
        ],
        "kyc_full_name": kyc_name or None,
        "default_remitter_name": kyc_name or None,
        "my_total": my_total,
        "my_this_month": my_this_month,
        "my_credits": my_credits,
        "circle_collected": circle_collected,
        "message": message,
        "source": "icici_ecollection",
        "simulate_enabled": simulate_enabled(),
    }
