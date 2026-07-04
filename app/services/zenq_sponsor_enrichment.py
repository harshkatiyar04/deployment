"""Batch enrichment for sponsor ZEQ inputs (Phase 2)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.microservices.vendor.models import VendorOrder
from app.models.mentor import MentorSession
from app.models.zenq import ZenqTargetLog
from app.services.sponsor_gamification import _order_clauses_for_circle


VALID_TARGET_STATUSES = frozenset({"none", "partial", "full", "stretch"})


def current_fy_quarter(now: Optional[datetime] = None) -> tuple[str, str]:
    now = now or datetime.now(timezone.utc)
    month = now.month
    if month in (4, 5, 6):
        q = "Q1"
    elif month in (7, 8, 9):
        q = "Q2"
    elif month in (10, 11, 12):
        q = "Q3"
    else:
        q = "Q4"
    year = now.year
    if month <= 3:
        fy = f"{year - 1}-{str(year)[-2:]}"
    else:
        fy = f"{year}-{str(year + 1)[-2:]}"
    return q, fy


def _since_naive(since: datetime) -> datetime:
    return since.replace(tzinfo=None) if since.tzinfo else since


async def batch_mentor_session_stats(
    db: AsyncSession,
    user_ids: list[str],
    since: datetime,
) -> dict[str, dict[str, float | int]]:
    if not user_ids:
        return {}
    since_naive = _since_naive(since)
    res = await db.execute(
        select(
            MentorSession.mentor_id,
            func.coalesce(func.sum(MentorSession.duration_hrs), 0.0),
            func.count(MentorSession.id),
            func.coalesce(
                func.sum(
                    case((MentorSession.inspiration_shared.isnot(None), 1), else_=0)
                ),
                0,
            ),
        )
        .where(
            MentorSession.mentor_id.in_(user_ids),
            MentorSession.created_at >= since_naive,
        )
        .group_by(MentorSession.mentor_id)
    )
    out: dict[str, dict[str, float | int]] = {}
    for uid, hours, count, inspire_count in res.all():
        out[uid] = {
            "mentor_session_mins": round(float(hours or 0.0) * 60.0, 1),
            "mentor_session_count": int(count or 0),
            "mentor_inspire_count": int(inspire_count or 0),
        }
    return out


async def batch_order_spend(
    db: AsyncSession,
    circle: SponsorCircle,
    user_ids: list[str],
    since: datetime,
) -> dict[str, float]:
    if not user_ids:
        return {}
    since_naive = _since_naive(since)
    member_res = await db.execute(
        select(CircleMember.user_id).where(CircleMember.circle_id == circle.id)
    )
    member_ids = [r[0] for r in member_res.all()]
    clauses = _order_clauses_for_circle(circle, member_ids)
    if not clauses:
        return {}

    res = await db.execute(
        select(VendorOrder.buyer_id, func.coalesce(func.sum(VendorOrder.total_amount), 0.0))
        .where(
            VendorOrder.buyer_id.in_(user_ids),
            VendorOrder.created_at >= since_naive,
            or_(*clauses),
        )
        .group_by(VendorOrder.buyer_id)
    )
    return {uid: round(float(total or 0.0), 2) for uid, total in res.all() if uid}


def batch_tenure_months(
    joined_by_user: dict[str, datetime],
    now: Optional[datetime] = None,
) -> dict[str, float]:
    now = now or datetime.now(timezone.utc)
    out: dict[str, float] = {}
    for uid, joined in joined_by_user.items():
        if not joined:
            out[uid] = 0.0
            continue
        j = joined
        if j.tzinfo is None:
            j = j.replace(tzinfo=timezone.utc)
        months = max(0.0, (now - j).days / 30.44)
        out[uid] = round(months, 1)
    return out


async def latest_target_status_by_sponsor(
    db: AsyncSession,
    circle_id: str,
    sponsor_ids: list[str],
    *,
    quarter: Optional[str] = None,
    fy: Optional[str] = None,
) -> dict[str, dict[str, Any]]:
    if not sponsor_ids:
        return {}
    q_key, fy_key = current_fy_quarter()
    quarter = quarter or q_key
    fy = fy or fy_key

    res = await db.execute(
        select(ZenqTargetLog)
        .where(
            ZenqTargetLog.circle_id == circle_id,
            ZenqTargetLog.sponsor_user_id.in_(sponsor_ids),
            ZenqTargetLog.quarter == quarter,
            ZenqTargetLog.fy == fy,
        )
        .order_by(ZenqTargetLog.created_at.desc())
    )
    out: dict[str, dict[str, Any]] = {}
    for row in res.scalars().all():
        if row.sponsor_user_id not in out:
            out[row.sponsor_user_id] = {
                "target_status": row.target_status,
                "notes": row.notes,
                "logged_at": row.created_at.isoformat() if row.created_at else None,
            }
    return out


async def resolve_circle_for_mentor(
    db: AsyncSession,
    *,
    mentor_circle_id: Optional[str],
    student_circle_name: str,
) -> Optional[str]:
    if mentor_circle_id:
        return mentor_circle_id
    name = (student_circle_name or "").strip()
    if not name:
        return None
    res = await db.execute(
        select(SponsorCircle.id).where(func.lower(SponsorCircle.name) == name.lower())
    )
    return res.scalar_one_or_none()
