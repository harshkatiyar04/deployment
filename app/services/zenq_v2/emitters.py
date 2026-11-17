"""Typed ledger emitters — chat/orders cannot invent SESSION/TARGET."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.zenq_v2.ledger import append_event

ALLOWED_CHAT = {"CHAT_ENCOUR", "CHAT_SUBST", "CHAT_SHARE", "CHAT_REACT"}
ALLOWED_KIA = {"KIA_PRACTICE", "KIA_PREP", "KIA_EFFECTIVE"}


def _with_idem(quality: Optional[dict[str, Any]], idempotency_key: Optional[str]) -> dict[str, Any]:
    q = dict(quality or {})
    if idempotency_key:
        q["idempotency_key"] = idempotency_key
    return q


async def emit_session(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
    minutes: float,
    session_id: Optional[str] = None,
    partner_flag: Optional[str] = None,
    bracket: str = "B",
    streak_weeks: int = 0,
    verified_by: str = "session_service",
    idempotency_key: Optional[str] = None,
    quality_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return await append_event(
        db,
        event_code="SESSION",
        actor_id=actor_id,
        circle_id=circle_id,
        minutes=minutes,
        session_id=session_id,
        partner_flag=partner_flag,
        bracket=bracket,
        streak_weeks=streak_weeks,
        verified_by=verified_by,
        quality_json=_with_idem(quality_json, idempotency_key),
    )


async def emit_target(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
    outcome: str,
    partner_flag: Optional[str] = None,
    bracket: str = "B",
    streak_weeks: int = 0,
    verified_by: str = "target_service",
    idempotency_key: Optional[str] = None,
) -> dict[str, Any]:
    if outcome not in ("none", "partial", "full", "stretch"):
        raise ValueError(f"invalid target outcome: {outcome}")
    return await append_event(
        db,
        event_code="TARGET",
        actor_id=actor_id,
        circle_id=circle_id,
        quality_json=_with_idem({"outcome": outcome}, idempotency_key),
        partner_flag=partner_flag,
        bracket=bracket,
        streak_weeks=streak_weeks,
        verified_by=verified_by,
    )


async def emit_chat(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
    chat_kind: str,
    bracket: str = "B",
    idempotency_key: Optional[str] = None,
    quality_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    code = chat_kind if chat_kind.startswith("CHAT_") else f"CHAT_{chat_kind.upper()}"
    if code not in ALLOWED_CHAT:
        raise ValueError(f"invalid chat code: {code}")
    return await append_event(
        db,
        event_code=code,
        actor_id=actor_id,
        circle_id=circle_id,
        bracket=bracket,
        verified_by="chat_classifier",
        quality_json=_with_idem(quality_json, idempotency_key),
    )


async def emit_kia(
    db: AsyncSession,
    *,
    actor_id: Optional[str],
    circle_id: str,
    kia_kind: str,
    bracket: str = "B",
    idempotency_key: Optional[str] = None,
) -> dict[str, Any]:
    code = kia_kind if kia_kind.startswith("KIA_") else f"KIA_{kia_kind.upper()}"
    if code not in ALLOWED_KIA:
        raise ValueError(f"invalid kia code: {code}")
    return await append_event(
        db,
        event_code=code,
        actor_id=actor_id or None,
        circle_id=circle_id,
        bracket=bracket,
        verified_by="kia_service",
        quality_json=_with_idem(None, idempotency_key),
    )


async def emit_pledge_paid(
    db: AsyncSession,
    *,
    actor_id: Optional[str],
    circle_id: str,
    pledge_inr: float,
    bracket: str = "B",
    idempotency_key: Optional[str] = None,
) -> dict[str, Any]:
    return await append_event(
        db,
        event_code="PLEDGE_PAID",
        actor_id=actor_id,
        circle_id=circle_id,
        quality_json=_with_idem({"pledge": pledge_inr}, idempotency_key),
        bracket=bracket,
        verified_by="payments",
    )


async def emit_reversal(
    db: AsyncSession,
    *,
    actor_id: Optional[str],
    circle_id: str,
    original_event_id: int,
    original_class: str,
    original_ip: float,
    idempotency_key: Optional[str] = None,
) -> dict[str, Any]:
    return await append_event(
        db,
        event_code="REVERSAL",
        actor_id=actor_id,
        circle_id=circle_id,
        quality_json=_with_idem(
            {"class": original_class, "ip_final": -abs(float(original_ip))},
            idempotency_key,
        ),
        reversal_of=original_event_id,
        verified_by="admin_reversal",
    )


async def emit_referral_activated(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
    idempotency_key: Optional[str] = None,
    quality_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return await append_event(
        db,
        event_code="REFERRAL_ACTIVATED",
        actor_id=actor_id,
        circle_id=circle_id,
        verified_by="referral_service",
        quality_json=_with_idem(quality_json, idempotency_key),
    )


async def emit_referral_anniversary(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
    idempotency_key: Optional[str] = None,
    quality_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return await append_event(
        db,
        event_code="REFERRAL_ANNIVERSARY",
        actor_id=actor_id,
        circle_id=circle_id,
        verified_by="referral_service",
        quality_json=_with_idem(quality_json, idempotency_key),
    )


async def emit_spark(
    db: AsyncSession,
    *,
    actor_id: str,
    circle_id: str,
    idempotency_key: Optional[str] = None,
    quality_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return await append_event(
        db,
        event_code="SPARK",
        actor_id=actor_id,
        circle_id=circle_id,
        verified_by="spark_service",
        quality_json=_with_idem(quality_json, idempotency_key),
    )
