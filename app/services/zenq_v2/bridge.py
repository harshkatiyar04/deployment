"""Fail-soft dual-run bridge: live hooks → zenq_v2 emitters (ZENQ_V2_LEDGER).

Never invents SESSION/TARGET from chat. Errors are logged and swallowed so
1.5.1 chat/mentor/payments paths never break.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.services.zenq_v2.chat_map import map_chat_event
from app.services.zenq_v2.emitters import (
    emit_chat,
    emit_kia,
    emit_pledge_paid,
    emit_session,
    emit_target,
)

logger = logging.getLogger(__name__)


async def resolve_bracket(db: AsyncSession, circle_id: str) -> str:
    try:
        row = (
            await db.execute(
                text(
                    """
                    SELECT bracket FROM "ZENK"."zenq_v2_circle_profile"
                    WHERE circle_id = CAST(:c AS uuid)
                    """
                ),
                {"c": circle_id},
            )
        ).scalar()
        if row and str(row).upper() in ("A", "B", "C"):
            return str(row).upper()
    except Exception:
        logger.debug("[zenq_v2] bracket lookup failed for %s", circle_id, exc_info=True)
    return "B"


async def bridge_chat_message(
    db: AsyncSession,
    *,
    message_id: str,
    circle_id: str,
    actor_user_id: str,
    ras_score: float,
    substantive: bool,
    shield_action: str,
) -> Optional[dict[str, Any]]:
    if not settings.zenq_v2_ledger:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_LEDGER off"}
    try:
        code = map_chat_event(
            ras_score=ras_score,
            substantive=substantive,
            shield_action=shield_action,
        )
        if code is None:
            reason = (
                "not_worthy"
                if (shield_action or "").strip().lower()
                not in ("block", "blocked", "reject", "denied", "drop")
                else "shield_blocked"
            )
            return {"ok": False, "skipped": True, "reason": reason}
        # Defense in depth: never award react-tier chat IP
        if code == "CHAT_REACT":
            return {"ok": False, "skipped": True, "reason": "chat_react_skipped"}
        bracket = await resolve_bracket(db, circle_id)
        return await emit_chat(
            db,
            actor_id=actor_user_id,
            circle_id=circle_id,
            chat_kind=code,
            bracket=bracket,
            idempotency_key=f"v2:chat:{message_id}",
            quality_json={
                "ras_score": ras_score,
                "substantive": substantive,
                "shield_action": shield_action,
                "mapped_code": code,
            },
        )
    except Exception:
        logger.exception("[zenq_v2] bridge_chat_message failed message=%s", message_id)
        return {"ok": False, "error": "bridge_failed"}


async def _member_of_circle(db: AsyncSession, user_id: str, circle_id: str) -> bool:
    try:
        row = (
            await db.execute(
                text(
                    """
                    SELECT 1 FROM "ZENK"."circle_members"
                    WHERE circle_id = CAST(:c AS uuid)
                      AND user_id = CAST(:u AS uuid)
                    LIMIT 1
                    """
                ),
                {"c": circle_id, "u": user_id},
            )
        ).scalar()
        return bool(row)
    except Exception:
        return True  # fail-soft → HOME credits


async def _streak_weeks(db: AsyncSession, member_id: str, circle_id: str) -> int:
    try:
        row = (
            await db.execute(
                text(
                    """
                    SELECT COALESCE(streak_weeks_end, 0)::int
                    FROM "ZENK"."zenq_v2_member_month"
                    WHERE member_id = CAST(:m AS uuid) AND circle_id = CAST(:c AS uuid)
                    ORDER BY month DESC LIMIT 1
                    """
                ),
                {"m": member_id, "c": circle_id},
            )
        ).scalar()
        return int(row or 0)
    except Exception:
        return 0


async def bridge_mentor_session(
    db: AsyncSession,
    *,
    session_id: str,
    circle_id: str,
    mentor_user_id: str,
    duration_hrs: float,
    partner_flag: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not settings.zenq_v2_ledger:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_LEDGER off"}
    try:
        minutes = max(0.0, float(duration_hrs or 0) * 60.0)
        bracket = await resolve_bracket(db, circle_id)
        # HOME if mentor belongs to the circle; otherwise ENGAGED (EPR pool, no home PCS).
        flag = (partner_flag or "").strip().upper()
        if flag not in ("HOME", "ENGAGED"):
            flag = (
                "HOME"
                if await _member_of_circle(db, mentor_user_id, circle_id)
                else "ENGAGED"
            )
        streak = await _streak_weeks(db, mentor_user_id, circle_id) if flag == "HOME" else 0
        return await emit_session(
            db,
            actor_id=mentor_user_id,
            circle_id=circle_id,
            minutes=minutes,
            session_id=session_id if _looks_uuid(session_id) else None,
            partner_flag=flag,
            bracket=bracket,
            streak_weeks=streak,
            verified_by="DEVICE",
            idempotency_key=f"v2:session:{session_id}",
            quality_json={
                "duration_hrs": duration_hrs,
                "source_session_id": session_id,
                "partner_flag": flag,
            },
        )
    except Exception:
        logger.exception("[zenq_v2] bridge_mentor_session failed session=%s", session_id)
        return {"ok": False, "error": "bridge_failed"}


async def bridge_target(
    db: AsyncSession,
    *,
    circle_id: str,
    sponsor_user_id: str,
    target_status: str,
    log_id: str,
) -> Optional[dict[str, Any]]:
    if not settings.zenq_v2_ledger:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_LEDGER off"}
    try:
        outcome = (target_status or "").lower().strip()
        if outcome not in ("none", "partial", "full", "stretch"):
            return {"ok": False, "skipped": True, "reason": f"bad_outcome:{outcome}"}
        bracket = await resolve_bracket(db, circle_id)
        streak = await _streak_weeks(db, sponsor_user_id, circle_id)
        return await emit_target(
            db,
            actor_id=sponsor_user_id,
            circle_id=circle_id,
            outcome=outcome,
            bracket=bracket,
            streak_weeks=streak,
            verified_by="COORDINATOR",
            idempotency_key=f"v2:target:{log_id}",
        )
    except Exception:
        logger.exception("[zenq_v2] bridge_target failed log=%s", log_id)
        return {"ok": False, "error": "bridge_failed"}


async def bridge_pledge_paid(
    db: AsyncSession,
    *,
    circle_id: str,
    amount_inr: float,
    txn_id: str,
    actor_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not settings.zenq_v2_ledger:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_LEDGER off"}
    try:
        bracket = await resolve_bracket(db, circle_id)
        return await emit_pledge_paid(
            db,
            actor_id=actor_id,
            circle_id=circle_id,
            pledge_inr=float(amount_inr or 0),
            bracket=bracket,
            idempotency_key=f"v2:pledge:{txn_id}",
        )
    except Exception:
        logger.exception("[zenq_v2] bridge_pledge_paid failed txn=%s", txn_id)
        return {"ok": False, "error": "bridge_failed"}


async def bridge_kia(
    db: AsyncSession,
    *,
    circle_id: str,
    actor_user_id: Optional[str],
    kia_kind: str,
    idempotency_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Live Kia practice/prep/effective → ledger. Fail-soft like chat bridge."""
    if not settings.zenq_v2_ledger:
        return {"ok": False, "skipped": True, "reason": "ZENQ_V2_LEDGER off"}
    kind = (kia_kind or "").strip().upper()
    if kind.startswith("KIA_"):
        kind = kind[4:]
    if kind not in ("PRACTICE", "PREP", "EFFECTIVE"):
        return {"ok": False, "skipped": True, "reason": f"bad_kia_kind:{kia_kind}"}
    try:
        bracket = await resolve_bracket(db, circle_id)
        key = idempotency_key or f"v2:kia:{kind.lower()}:{circle_id}:{actor_user_id or 'circle'}"
        return await emit_kia(
            db,
            actor_id=actor_user_id,
            circle_id=circle_id,
            kia_kind=kind,
            bracket=bracket,
            idempotency_key=key,
        )
    except Exception:
        logger.exception(
            "[zenq_v2] bridge_kia failed circle=%s kind=%s", circle_id, kia_kind
        )
        return {"ok": False, "error": "bridge_failed"}


def _looks_uuid(value: str) -> bool:
    s = (value or "").strip()
    if len(s) != 36:
        return False
    parts = s.split("-")
    return len(parts) == 5
