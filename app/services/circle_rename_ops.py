"""Circle rename requests — leader-only, 90-day cooldown, ZenK admin approval."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.models.circle_ops import (
    RENAME_COOLDOWN_DAYS,
    REQUEST_CIRCLE_RENAME,
    STATUS_PENDING,
    CircleAdminRequest,
)
from app.models.signup import SignupRequest
from app.services.circle_membership_ops import request_to_dict
from app.services.circle_name_validation import assert_circle_name_available, normalize_circle_name


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def next_rename_eligible_at(circle: SponsorCircle) -> datetime | None:
    anchor = _as_utc(circle.name_changed_at) or _as_utc(circle.created_at)
    if not anchor:
        return None
    return anchor + timedelta(days=RENAME_COOLDOWN_DAYS)


async def _pending_rename(db: AsyncSession, circle_id: str) -> CircleAdminRequest | None:
    res = await db.execute(
        select(CircleAdminRequest)
        .where(
            CircleAdminRequest.circle_id == circle_id,
            CircleAdminRequest.request_type == REQUEST_CIRCLE_RENAME,
            CircleAdminRequest.status == STATUS_PENDING,
        )
        .order_by(CircleAdminRequest.created_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def build_rename_status(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
) -> dict[str, Any]:
    pending = await _pending_rename(db, circle.id)
    eligible_at = next_rename_eligible_at(circle)
    now = _utc_now()
    cooldown_active = bool(eligible_at and now < eligible_at)
    can_request = pending is None and not cooldown_active

    reason = None
    if pending:
        reason = "A rename request is already awaiting ZenK admin review."
    elif cooldown_active and eligible_at:
        reason = (
            f"Circle names can be changed once every {RENAME_COOLDOWN_DAYS} days. "
            f"Next eligible date: {eligible_at.date().isoformat()}."
        )

    pending_dict = (
        request_to_dict(pending, circle_name=circle.name) if pending else None
    )

    return {
        "can_request": can_request,
        "current_name": circle.name,
        "next_eligible_at": eligible_at.isoformat() if eligible_at else None,
        "cooldown_days": RENAME_COOLDOWN_DAYS,
        "pending_request": pending_dict,
        "blocked_reason": reason,
        "policy_note": (
            f"Only the circle leader can request a rename. Changes require ZenK admin approval "
            f"and are limited to once every {RENAME_COOLDOWN_DAYS} days."
        ),
    }


async def request_circle_rename(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    leader: SignupRequest,
    new_name: str,
    comment: str,
) -> CircleAdminRequest:
    reason = (comment or "").strip()
    if len(reason) < 10:
        raise ValueError("Please explain why you want to rename the circle (at least 10 characters).")

    status = await build_rename_status(db, circle=circle)
    if not status["can_request"]:
        raise ValueError(status["blocked_reason"] or "Rename is not available right now.")

    cleaned = normalize_circle_name(new_name)
    if len(cleaned) < 2:
        raise ValueError("Circle name must be at least 2 characters.")

    current_clean = normalize_circle_name(circle.name or "")
    if cleaned.lower() == current_clean.lower():
        raise ValueError("New name must be different from the current circle name.")

    try:
        await assert_circle_name_available(db, cleaned, exclude_circle_id=circle.id)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    req = CircleAdminRequest(
        id=str(uuid.uuid4()),
        circle_id=circle.id,
        request_type=REQUEST_CIRCLE_RENAME,
        status=STATUS_PENDING,
        requested_by_user_id=leader.id,
        requested_by_name=leader.full_name,
        current_circle_name=circle.name,
        requested_circle_name=cleaned[:255],
        leader_comment=reason,
    )
    db.add(req)
    await db.flush()
    return req


async def apply_approved_circle_rename(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    req: CircleAdminRequest,
    leader_name: str,
) -> str:
    if not req.requested_circle_name:
        raise ValueError("Missing requested circle name on rename request.")

    old_name = circle.name
    circle.name = await assert_circle_name_available(
        db,
        req.requested_circle_name,
        exclude_circle_id=circle.id,
    )
    circle.name_changed_at = _utc_now()

    from app.services.kia_event_briefings import emit_circle_renamed

    await emit_circle_renamed(
        db,
        circle=circle,
        leader_name=leader_name or "Circle leader",
        old_name=old_name,
    )
    return old_name
