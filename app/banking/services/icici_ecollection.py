"""
ICICI eCollection MH7 — inbound Validation + Credit Confirmation.

Bank calls ZenK (not the other way around). Encryption algorithm and exact
JSON tag names will be locked after ICICI returns sample packets for the filled BRS.
Until then, plaintext JSON is accepted when ICICI_ECOLLECTION_PLAINTEXT=true (local/UAT sim).
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.banking.models.icici_ecollection import (
    EVENT_CREDIT_CONFIRM,
    EVENT_VALIDATE,
    TXN_ACCEPTED,
    TXN_CREDITED,
    TXN_PENDING_VALIDATE,
    TXN_REJECTED,
    EcollectionEvent,
    EcollectionTransaction,
    EcollectionVan,
)

logger = logging.getLogger(__name__)

# BRS payment-mode mapping defaults (override via settings later if bank requires other codes)
MODE_MAP = {
    "NEFT": "N",
    "RTGS": "R",
    "IMPS": "I",
    "FT": "FT",
    "FUND TRANSFER": "FT",
    "UPI": "U",
}


def _first(payload: dict[str, Any], *keys: str) -> Any:
    lower = {str(k).lower(): v for k, v in payload.items()}
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
        lk = key.lower()
        if lk in lower and lower[lk] not in (None, ""):
            return lower[lk]
    return None


def normalize_amount_to_paise(raw: Any) -> tuple[str, int]:
    """Return (display_inr, amount_paise) — BRS allows 100 / 100.0 / 100.00."""
    try:
        d = Decimal(str(raw).strip().replace(",", ""))
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError("Invalid TRANSACTION AMOUNT") from exc
    if d <= 0:
        raise ValueError("Amount must be positive")
    paise = int((d * 100).quantize(Decimal("1")))
    display = f"{d.quantize(Decimal('0.01'))}"
    return display, paise


def normalize_mode(raw: Any) -> Optional[str]:
    if raw is None or raw == "":
        return None
    s = str(raw).strip().upper()
    if s in MODE_MAP.values():
        return s
    return MODE_MAP.get(s, s[:16])


def parse_validate_request(payload: dict[str, Any]) -> dict[str, Any]:
    client_code = str(_first(payload, "CUSTOMER CODE", "CUSTOMER_CODE", "customerCode") or "").strip()
    van = str(
        _first(payload, "VIRTUAL ACCOUNT NUMBER", "VAN", "virtualAccountNumber") or ""
    ).strip()
    amount_raw = _first(payload, "TRANSACTION AMOUNT", "AMOUNT", "transactionAmount")
    currency = str(_first(payload, "CURRENCY CODE", "CURRENCY_CODE", "currencyCode") or "INR").strip()
    utr = str(_first(payload, "UTR", "utr") or "").strip()
    tran_date = str(_first(payload, "DATE", "TRAN_DATE", "tranDate") or "").strip() or None
    mode = normalize_mode(_first(payload, "PAYMENT MODE", "PAYMENT_MODE", "paymentMode"))
    sender_name = _first(payload, "SENDER NAME", "REMITTERNAME", "remitterName")
    sender_acc = _first(payload, "SENDER ACCOUNT NUMBER", "REMITTER_ACCNO", "remitterAccNo")
    sender_ifsc = _first(payload, "SENDER IFSC", "REMITTER_IFSC", "remitterIfsc")

    if not client_code or len(client_code) > 6:
        raise ValueError("CUSTOMER CODE required (max 6)")
    if not van:
        raise ValueError("VIRTUAL ACCOUNT NUMBER required")
    if not utr:
        raise ValueError("UTR required")
    amount_inr, amount_paise = normalize_amount_to_paise(amount_raw)
    if currency.upper() != "INR":
        raise ValueError("Only INR supported")

    return {
        "client_code": client_code.upper(),
        "van": van.upper(),
        "amount_inr": amount_inr,
        "amount_paise": amount_paise,
        "currency_code": "INR",
        "utr": utr,
        "bank_tran_date": tran_date,
        "payment_mode": mode,
        "remitter_name": str(sender_name)[:80] if sender_name else None,
        "remitter_account": str(sender_acc)[:40] if sender_acc else None,
        "remitter_ifsc": str(sender_ifsc)[:16] if sender_ifsc else None,
    }


def parse_credit_confirm_request(payload: dict[str, Any]) -> dict[str, Any]:
    # Credit confirm uses slightly different tag names in BRS table 4
    mapped = {
        **payload,
        "CUSTOMER CODE": _first(payload, "CUSTOMER_CODE", "CUSTOMER CODE"),
        "VIRTUAL ACCOUNT NUMBER": _first(payload, "VAN", "VIRTUAL ACCOUNT NUMBER"),
        "TRANSACTION AMOUNT": _first(payload, "AMOUNT", "TRANSACTION AMOUNT"),
        "CURRENCY CODE": _first(payload, "CURRENCY_CODE", "CURRENCY CODE"),
        "DATE": _first(payload, "TRAN_DATE", "DATE"),
        "SENDER NAME": _first(payload, "REMITTERNAME", "SENDER NAME"),
        "SENDER ACCOUNT NUMBER": _first(payload, "REMITTER_ACCNO", "SENDER ACCOUNT NUMBER"),
        "SENDER IFSC": _first(payload, "REMITTER_IFSC", "SENDER IFSC"),
        "PAYMENT MODE": _first(payload, "PAYMENT_MODE", "PAYMENT MODE"),
    }
    return parse_validate_request(mapped)


async def _log_event(
    db: AsyncSession,
    *,
    event_type: str,
    request_payload: dict,
    response_payload: dict,
    http_status: int,
    client_ip: Optional[str],
    utr: Optional[str] = None,
    transaction_id: Optional[str] = None,
) -> None:
    db.add(
        EcollectionEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            transaction_id=transaction_id,
            utr=utr,
            request_payload=request_payload,
            response_payload=response_payload,
            http_status=http_status,
            client_ip=client_ip,
        )
    )


async def _find_van(db: AsyncSession, van: str, client_code: str) -> Optional[EcollectionVan]:
    res = await db.execute(
        select(EcollectionVan).where(
            EcollectionVan.van == van,
            EcollectionVan.client_code == client_code,
            EcollectionVan.is_active.is_(True),
        )
    )
    return res.scalar_one_or_none()


async def _get_txn(db: AsyncSession, utr: str, amount_paise: int) -> Optional[EcollectionTransaction]:
    res = await db.execute(
        select(EcollectionTransaction).where(
            EcollectionTransaction.utr == utr,
            EcollectionTransaction.amount_paise == amount_paise,
        )
    )
    return res.scalar_one_or_none()


def _reject(reason: str, code: str = "REJECT") -> dict[str, str]:
    return {"STATUS": "R", "REJECT REASON": reason[:25], "REJECTION CODE": code[:15]}


def _accept() -> dict[str, str]:
    return {"STATUS": "A", "REJECT REASON": "", "REJECTION CODE": ""}


async def handle_validation(
    db: AsyncSession,
    payload: dict[str, Any],
    *,
    client_ip: Optional[str] = None,
) -> tuple[dict[str, Any], int]:
    try:
        data = parse_validate_request(payload)
    except ValueError as exc:
        resp = _reject(str(exc)[:25], "BAD_REQ")
        await _log_event(
            db,
            event_type=EVENT_VALIDATE,
            request_payload=payload,
            response_payload=resp,
            http_status=200,
            client_ip=client_ip,
        )
        return resp, 200

    existing = await _get_txn(db, data["utr"], data["amount_paise"])
    if existing:
        # Idempotent: repeat same decision
        if existing.status == TXN_REJECTED:
            resp = _reject(existing.reject_reason or "REJECTED", existing.reject_code or "REJ")
        else:
            resp = _accept()
        await _log_event(
            db,
            event_type=EVENT_VALIDATE,
            request_payload=payload,
            response_payload=resp,
            http_status=200,
            client_ip=client_ip,
            utr=data["utr"],
            transaction_id=existing.id,
        )
        return resp, 200

    expected_code = (settings.icici_ecollection_client_code or "").strip().upper()
    if expected_code and data["client_code"] != expected_code:
        resp = _reject("BAD CLIENT CODE", "CLIENT")
        await _log_event(
            db,
            event_type=EVENT_VALIDATE,
            request_payload=payload,
            response_payload=resp,
            http_status=200,
            client_ip=client_ip,
            utr=data["utr"],
        )
        return resp, 200

    van_row = await _find_van(db, data["van"], data["client_code"])
    if not van_row:
        # Soft-UAT mode: optionally auto-accept unknown VAN when enabled
        if not settings.icici_ecollection_accept_unknown_van:
            resp = _reject("UNKNOWN VAN", "VAN")
            txn = EcollectionTransaction(
                id=str(uuid.uuid4()),
                status=TXN_REJECTED,
                reject_reason="UNKNOWN VAN",
                reject_code="VAN",
                circle_id=None,
                **{k: data[k] for k in (
                    "utr", "amount_paise", "amount_inr", "currency_code", "van",
                    "client_code", "payment_mode", "remitter_name", "remitter_account",
                    "remitter_ifsc", "bank_tran_date",
                )},
            )
            db.add(txn)
            await _log_event(
                db,
                event_type=EVENT_VALIDATE,
                request_payload=payload,
                response_payload=resp,
                http_status=200,
                client_ip=client_ip,
                utr=data["utr"],
                transaction_id=txn.id,
            )
            return resp, 200

    txn = EcollectionTransaction(
        id=str(uuid.uuid4()),
        status=TXN_ACCEPTED,
        circle_id=van_row.circle_id if van_row else None,
        **{k: data[k] for k in (
            "utr", "amount_paise", "amount_inr", "currency_code", "van",
            "client_code", "payment_mode", "remitter_name", "remitter_account",
            "remitter_ifsc", "bank_tran_date",
        )},
    )
    db.add(txn)
    resp = _accept()
    await _log_event(
        db,
        event_type=EVENT_VALIDATE,
        request_payload=payload,
        response_payload=resp,
        http_status=200,
        client_ip=client_ip,
        utr=data["utr"],
        transaction_id=txn.id,
    )
    return resp, 200


async def handle_credit_confirm(
    db: AsyncSession,
    payload: dict[str, Any],
    *,
    client_ip: Optional[str] = None,
) -> tuple[dict[str, Any], int]:
    try:
        data = parse_credit_confirm_request(payload)
    except ValueError as exc:
        resp = {"STATUS": "R", "Remarks": str(exc)[:35]}
        await _log_event(
            db,
            event_type=EVENT_CREDIT_CONFIRM,
            request_payload=payload,
            response_payload=resp,
            http_status=200,
            client_ip=client_ip,
        )
        return resp, 200

    txn = await _get_txn(db, data["utr"], data["amount_paise"])
    if not txn:
        # Confirm without prior validate — create credited if VAN known (edge case)
        van_row = await _find_van(db, data["van"], data["client_code"])
        if not van_row and not settings.icici_ecollection_accept_unknown_van:
            resp = {"STATUS": "R", "Remarks": "UNKNOWN UTR/VAN"}
            await _log_event(
                db,
                event_type=EVENT_CREDIT_CONFIRM,
                request_payload=payload,
                response_payload=resp,
                http_status=200,
                client_ip=client_ip,
                utr=data["utr"],
            )
            return resp, 200
        txn = EcollectionTransaction(
            id=str(uuid.uuid4()),
            status=TXN_ACCEPTED,
            circle_id=van_row.circle_id if van_row else None,
            **{k: data[k] for k in (
                "utr", "amount_paise", "amount_inr", "currency_code", "van",
                "client_code", "payment_mode", "remitter_name", "remitter_account",
                "remitter_ifsc", "bank_tran_date",
            )},
        )
        db.add(txn)
        await db.flush()

    if txn.status == TXN_REJECTED:
        resp = {"STATUS": "R", "Remarks": "PREVIOUSLY REJECTED"}
        await _log_event(
            db,
            event_type=EVENT_CREDIT_CONFIRM,
            request_payload=payload,
            response_payload=resp,
            http_status=200,
            client_ip=client_ip,
            utr=data["utr"],
            transaction_id=txn.id,
        )
        return resp, 200

    if txn.status == TXN_CREDITED and txn.ledger_posted:
        # Idempotent success
        resp = {"STATUS": "A", "Remarks": "ALREADY CREDITED"}
        await _log_event(
            db,
            event_type=EVENT_CREDIT_CONFIRM,
            request_payload=payload,
            response_payload=resp,
            http_status=200,
            client_ip=client_ip,
            utr=data["utr"],
            transaction_id=txn.id,
        )
        return resp, 200

    txn.status = TXN_CREDITED
    txn.credited_at = datetime.now(timezone.utc)
    txn.updated_at = datetime.now(timezone.utc)
    # Ledger post into circle.budget_collected — enabled when circle_id present
    if txn.circle_id and not txn.ledger_posted:
        try:
            from app.chat.models import SponsorCircle

            cres = await db.execute(select(SponsorCircle).where(SponsorCircle.id == txn.circle_id))
            circle = cres.scalar_one_or_none()
            if circle:
                rupees = int(round(txn.amount_paise / 100))
                circle.budget_collected = int(circle.budget_collected or 0) + rupees
                txn.ledger_posted = True
        except Exception:
            logger.exception("eCollection ledger post failed utr=%s", txn.utr)

    resp = {"STATUS": "A", "Remarks": "OK"}
    await _log_event(
        db,
        event_type=EVENT_CREDIT_CONFIRM,
        request_payload=payload,
        response_payload=resp,
        http_status=200,
        client_ip=client_ip,
        utr=data["utr"],
        transaction_id=txn.id,
    )
    return resp, 200


def build_van(client_code: str, suffix: str) -> str:
    code = re.sub(r"[^A-Z0-9]", "", (client_code or "").upper())[:6]
    suf = re.sub(r"[^A-Z0-9]", "", (suffix or "").upper())[:24]
    return f"{code}{suf}"


async def register_van(
    db: AsyncSession,
    *,
    client_code: str,
    suffix: str,
    circle_id: str,
    member_user_id: Optional[str] = None,
    purpose: Optional[str] = None,
) -> EcollectionVan:
    van = build_van(client_code, suffix)
    row = EcollectionVan(
        id=str(uuid.uuid4()),
        client_code=client_code.upper()[:6],
        van_suffix=suffix.upper()[:30],
        van=van,
        circle_id=circle_id,
        member_user_id=member_user_id,
        purpose=(purpose or "")[:120] or None,
        is_active=True,
    )
    db.add(row)
    await db.flush()
    return row
