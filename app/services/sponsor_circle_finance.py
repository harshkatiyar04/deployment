"""Live circle finance: budget, eCollection credits, orders, and disbursements."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banking.models.icici_ecollection import TXN_CREDITED, EcollectionTransaction
from app.chat.models import CircleMember, SponsorCircle
from app.microservices.vendor.models import VendorOrder, VendorProduct
from app.models.circle_ops import DISBURSEMENT_PAID, CircleDisbursement, CirclePayee
from app.models.signup import SignupRequest

_DISBURSE_CATEGORY_LABELS = {
    "school_fees": "School Fees",
    "supplies": "Supplies",
    "books": "Books",
    "uniform": "Uniform",
    "other": "Other",
}


def _fmt_date(dt: datetime | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%d %b")


def _fmt_inr(n: int) -> str:
    n = int(n or 0)
    if n < 0:
        return f"-₹{abs(n):,}"
    return f"₹{n:,}"


def _category_for_order(order_type: str) -> str:
    if order_type == "student":
        return "Student"
    if order_type == "personal":
        return "Personal"
    return "Operational"


def _norm_name(s: str | None) -> str:
    return " ".join((s or "").strip().lower().split())


def _role_match_priority(m: dict) -> int:
    """Lower = preferred payer when several circle users share the same KYC name."""
    badge = (m.get("badge") or "").lower()
    role = (m.get("cm_role") or m.get("role") or "").lower()
    if badge == "leader" or role in ("lead", "sponsor_leader", "coordinator", "leader"):
        return 0
    if role in ("sponsor", "sponsor_member", "member"):
        return 1
    if role in ("parent", "guardian"):
        return 2
    if role in ("student",):
        return 9
    return 5


def _pick_unique_best(hits: list[dict]) -> Optional[dict]:
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    ranked = sorted(hits, key=_role_match_priority)
    # Prefer unique best role tier (e.g. one leader + one student → leader)
    best_p = _role_match_priority(ranked[0])
    top = [h for h in ranked if _role_match_priority(h) == best_p]
    if len(top) == 1:
        return top[0]
    return None


def _match_remitter_to_member(
    remitter_name: str | None,
    members: list[dict],
) -> Optional[dict]:
    """
    Match bank remitter → circle member KYC / legal name.
    Prefer exact full-name. If several members share that KYC (e.g. student
    profile wrongly set to the leader's name), attribute to the best role
    (leader / sponsor before student).
    """
    rem = _norm_name(remitter_name)
    if not rem:
        return None

    exact = [
        m
        for m in members
        if _norm_name(m.get("match_name") or m.get("name")) == rem
    ]
    picked = _pick_unique_best(exact)
    if picked:
        return picked
    if exact:
        # Same role tier duplicates — cannot safely attribute
        return None

    tokens = [t for t in rem.split() if len(t) >= 2]
    if len(tokens) >= 2:
        first, last = tokens[0], tokens[-1]
        hits = []
        for m in members:
            full = _norm_name(m.get("match_name") or m.get("name"))
            if full and first in full.split() and last in full.split():
                hits.append(m)
        return _pick_unique_best(hits)

    if len(tokens) == 1:
        only = tokens[0]
        hits = [
            m
            for m in members
            if _norm_name(m.get("match_name") or m.get("name")) == only
        ]
        return _pick_unique_best(hits)
    return None


def _txn_amount_inr(txn: EcollectionTransaction) -> int:
    if txn.amount_paise is not None:
        return max(0, int(txn.amount_paise) // 100)
    try:
        return max(0, int(round(float(txn.amount_inr or 0))))
    except (TypeError, ValueError):
        return 0


async def _circle_member_ids(db: AsyncSession, circle_id: str) -> list[str]:
    res = await db.execute(
        select(CircleMember.user_id).where(CircleMember.circle_id == circle_id)
    )
    return [r[0] for r in res.all()]


async def fetch_circle_orders(
    db: AsyncSession,
    circle: SponsorCircle,
) -> list[tuple[VendorOrder, Optional[str]]]:
    """
    Circle-fund marketplace orders only (student cart / student fund).
    Personal member purchases are excluded from circle statement & spend.
    """
    member_ids = await _circle_member_ids(db, circle.id)
    clauses = []
    if circle.name:
        clauses.append(
            (VendorOrder.circle_name == circle.name)
            & (VendorOrder.order_type == "student")
        )
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


async def fetch_paid_disbursements(
    db: AsyncSession,
    circle_id: str,
) -> list[tuple[CircleDisbursement, CirclePayee | None]]:
    res = await db.execute(
        select(CircleDisbursement, CirclePayee)
        .outerjoin(CirclePayee, CirclePayee.id == CircleDisbursement.payee_id)
        .where(
            CircleDisbursement.circle_id == circle_id,
            CircleDisbursement.status == DISBURSEMENT_PAID,
        )
        .order_by(
            CircleDisbursement.paid_at.asc().nullsfirst(),
            CircleDisbursement.created_at.asc(),
        )
    )
    return list(res.all())


async def compute_spent_from_orders(db: AsyncSession, circle: SponsorCircle) -> int:
    """Marketplace order spend only (legacy helper). Prefer compute_circle_spent."""
    rows = await fetch_circle_orders(db, circle)
    return sum(int(round(float(o.total_amount or 0))) for o, _ in rows)


async def compute_circle_spent(db: AsyncSession, circle: SponsorCircle) -> int:
    """Same definition as Circle Banking: orders + paid disbursements."""
    order_spent = await compute_spent_from_orders(db, circle)
    paid = await fetch_paid_disbursements(db, circle.id)
    paid_out = sum(int(d.amount_inr or 0) for d, _ in paid)
    return order_spent + paid_out


def _as_utc(dt: datetime | None) -> datetime:
    if not dt:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def fetch_credited_ecollection(
    db: AsyncSession,
    circle_id: str,
) -> list[EcollectionTransaction]:
    res = await db.execute(
        select(EcollectionTransaction)
        .where(
            EcollectionTransaction.circle_id == circle_id,
            EcollectionTransaction.status == TXN_CREDITED,
        )
        .order_by(
            EcollectionTransaction.credited_at.asc().nullsfirst(),
            EcollectionTransaction.created_at.asc(),
        )
    )
    return list(res.scalars().all())


def budget_numbers(
    circle: SponsorCircle,
    spent: int,
    *,
    collected_override: int | None = None,
) -> dict[str, int]:
    total = int(circle.annual_budget or 0)
    collected = (
        int(collected_override)
        if collected_override is not None
        else int(circle.budget_collected or 0)
    )
    available_balance = max(0, collected - spent)
    remaining_target = max(0, total - spent) if total > 0 else 0
    return {
        "total_budget": total,
        "spent": spent,
        "collected": collected,
        "available_balance": available_balance,
        "remaining_target": remaining_target,
        "balance_to_spend": available_balance,
    }


async def build_statement(
    db: AsyncSession,
    circle: SponsorCircle,
) -> dict:
    """
    Chronological circle fund ledger: ICICI credits − student-fund orders − paid disbursements.
    Running balance is not clamped (pre-funding spend shows negative / overdrawn).
    """
    order_rows = await fetch_circle_orders(db, circle)
    paid_rows = await fetch_paid_disbursements(db, circle.id)
    order_spent = sum(int(round(float(o.total_amount or 0))) for o, _ in order_rows)
    paid_out = sum(int(d.amount_inr or 0) for d, _ in paid_rows)
    spent = order_spent + paid_out

    credits = await fetch_credited_ecollection(db, circle.id)
    van_collected = sum(_txn_amount_inr(t) for t in credits)
    collected = van_collected if credits else int(circle.budget_collected or 0)
    nums = budget_numbers(circle, spent, collected_override=collected)

    events: list[tuple[datetime, int, dict]] = []
    seq = 0

    if credits:
        for txn in credits:
            amt = _txn_amount_inr(txn)
            if amt <= 0:
                continue
            remitter = (txn.remitter_name or "Remitter").strip() or "Remitter"
            mode = (txn.payment_mode or "").strip().upper() or "NEFT"
            utr = (txn.utr or "")[:16]
            when = txn.credited_at or txn.created_at
            events.append(
                (
                    _as_utc(when),
                    seq,
                    {
                        "kind": "credit",
                        "amount": amt,
                        "date": _fmt_date(when) or "—",
                        "type": "Credit",
                        "tag": "credit",
                        "desc": f"Bank credit — {remitter} · {mode}"
                        + (f" · {utr}" if utr else ""),
                    },
                )
            )
            seq += 1
    elif nums["collected"] > 0:
        events.append(
            (
                datetime.min.replace(tzinfo=timezone.utc),
                seq,
                {
                    "kind": "credit",
                    "amount": nums["collected"],
                    "date": "—",
                    "type": "Opening",
                    "tag": "opening",
                    "desc": "Recorded collections (FY)",
                },
            )
        )
        seq += 1

    for order, product_name in order_rows:
        amt = int(round(float(order.total_amount or 0)))
        if amt <= 0:
            continue
        events.append(
            (
                _as_utc(order.created_at),
                seq,
                {
                    "kind": "debit",
                    "amount": amt,
                    "date": _fmt_date(order.created_at) or "—",
                    "type": _category_for_order(order.order_type or ""),
                    "tag": "student" if order.order_type == "student" else "order",
                    "desc": (product_name or "Marketplace order")
                    + (f" — {order.buyer_name}" if order.buyer_name else ""),
                },
            )
        )
        seq += 1

    for disbursement, payee in paid_rows:
        amt = int(disbursement.amount_inr or 0)
        if amt <= 0:
            continue
        when = disbursement.paid_at or disbursement.created_at
        vendor = (payee.display_name if payee else None) or "Payee"
        cat = _DISBURSE_CATEGORY_LABELS.get(
            (disbursement.category or "").lower(), "Other"
        )
        desc = f"Vendor payment — {vendor}"
        if disbursement.description:
            desc += f" · {disbursement.description}"
        events.append(
            (
                _as_utc(when),
                seq,
                {
                    "kind": "debit",
                    "amount": amt,
                    "date": _fmt_date(when) or "—",
                    "type": cat,
                    "tag": "disburse",
                    "desc": desc,
                },
            )
        )
        seq += 1

    # Oldest → newest so running balance is meaningful
    events.sort(key=lambda e: (e[0], e[1]))
    ledger: list[dict] = []
    running = 0
    credit_total = 0
    debit_total = 0
    for _, _, ev in events:
        amt = int(ev["amount"] or 0)
        if ev["kind"] == "credit":
            running += amt
            credit_total += amt
            ledger.append(
                {
                    "date": ev["date"],
                    "type": ev["type"],
                    "tag": ev["tag"],
                    "desc": ev["desc"],
                    "debit": "—",
                    "credit": _fmt_inr(amt),
                    "balance": _fmt_inr(running),
                }
            )
        else:
            running -= amt
            debit_total += amt
            ledger.append(
                {
                    "date": ev["date"],
                    "type": ev["type"],
                    "tag": ev["tag"],
                    "desc": ev["desc"],
                    "debit": _fmt_inr(amt),
                    "credit": "—",
                    "balance": _fmt_inr(running),
                }
            )

    closing = running
    expected = int(collected) - int(spent)
    ledger_ok = (
        closing == expected
        and credit_total == int(collected)
        and debit_total == int(spent)
    )
    warning = None
    if ledger and not ledger_ok:
        warning = (
            "Ledger closing balance does not match Collected − Spent. "
            f"Closing {_fmt_inr(closing)} vs expected {_fmt_inr(expected)}."
        )

    return {
        **nums,
        # Statement uses true fund position (may be negative if overdrawn)
        "available_balance": expected,
        "balance_to_spend": max(0, expected),
        "fy_label": circle.fy_label or "2025-26",
        "circle_name": circle.name,
        "rows": ledger,
        "has_data": bool(ledger) or nums["total_budget"] > 0 or spent > 0 or van_collected > 0,
        "closing_balance": closing,
        "credit_total": credit_total,
        "debit_total": debit_total,
        "ledger_ok": ledger_ok,
        "warning": warning,
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
    """Per-member totals attributed from ICICI eCollection credited remittances."""
    from app.services.student_circle_privacy import display_name_for_roster

    res = await db.execute(
        select(CircleMember, SignupRequest)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(CircleMember.circle_id == circle.id)
        .order_by(SignupRequest.full_name)
    )
    members: list[dict] = []
    for cm, signup in res.all():
        name, initials, role_label = await display_name_for_roster(
            db, signup, cm_role=cm.role or "sponsor"
        )
        badge = ""
        if cm.role in ("lead", "sponsor_leader", "coordinator"):
            badge = "leader"
        kyc = (signup.full_name or "").strip()
        members.append(
            {
                "name": name,
                "match_name": kyc or (name or "").strip(),
                "kyc_name": kyc or None,
                "initials": initials,
                "role": role_label,
                "role_label": role_label,
                "cm_role": (cm.role or "sponsor").strip().lower(),
                "total_contributed": 0,
                "this_month": 0,
                "pct": None,
                "badge": badge,
                "zenq": None,
            }
        )

    credits = await fetch_credited_ecollection(db, circle.id)
    now = datetime.now(timezone.utc)
    unmatched_total = 0
    attributed_total = 0
    matched_credit_count = 0
    unmatched_credits: list[dict] = []

    for txn in credits:
        amt = _txn_amount_inr(txn)
        when = txn.credited_at or txn.created_at
        if when and when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        remitter = (txn.remitter_name or "").strip() or None
        matched = _match_remitter_to_member(txn.remitter_name, members)
        if matched:
            matched["total_contributed"] = int(matched["total_contributed"] or 0) + amt
            attributed_total += amt
            matched_credit_count += 1
            if when and when.year == now.year and when.month == now.month:
                matched["this_month"] = int(matched["this_month"] or 0) + amt
        else:
            unmatched_total += amt
            unmatched_credits.append(
                {
                    "remitter_name": remitter or "(blank remitter)",
                    "amount": amt,
                    "utr": (txn.utr or "")[:20] or None,
                    "payment_mode": txn.payment_mode,
                    "credited_at": when.isoformat() if when else None,
                }
            )

    # Newest unmatched first for the leader review list
    unmatched_credits.sort(key=lambda r: r.get("credited_at") or "", reverse=True)

    van_collected = sum(_txn_amount_inr(t) for t in credits)
    spent = await compute_circle_spent(db, circle)
    collected = van_collected if credits else int(circle.budget_collected or 0)
    nums = budget_numbers(circle, spent, collected_override=collected)
    total_budget = nums["total_budget"]
    funded_pct = round((collected / total_budget) * 100) if total_budget > 0 else None

    # Share = % of attributed pool (not of unmatched), so rows sum ~100% among contributors
    share_base = attributed_total if attributed_total > 0 else 0
    for m in members:
        total = int(m["total_contributed"] or 0)
        if share_base > 0 and total > 0:
            m["pct"] = round((total / share_base) * 100)
        if not credits:
            m["total_contributed"] = None
            m["this_month"] = None
        m.pop("match_name", None)
        m.pop("cm_role", None)

    if credits:
        message = (
            f"{matched_credit_count} of {len(credits)} bank credit"
            f"{'' if len(credits) == 1 else 's'} matched to a member KYC name. "
            "Unmatched remittances still count in Collected / Statement."
        )
    else:
        message = (
            "No bank credits yet. Simulate a credit in Circle Banking → Collect "
            "(or Contribute for members), or wait for an ICICI remittance to the circle VAN."
        )

    return {
        "tracking_available": True,
        "members": members,
        "total_collected": collected if collected > 0 else None,
        "total_budget": total_budget if total_budget > 0 else None,
        "funded_pct": funded_pct,
        "spent": nums["spent"],
        "unmatched_total": unmatched_total,
        "attributed_total": attributed_total,
        "credit_count": len(credits),
        "matched_credit_count": matched_credit_count,
        "unmatched_credits": unmatched_credits[:40],
        "source": "icici_ecollection",
        "message": message,
    }
