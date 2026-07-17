"""Persist and query landing survey feedback + visit beacons."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import to_utc_iso
from app.models.landing_feedback import LandingFeedbackSubmission, LandingVisit


def feedback_to_dict(row: LandingFeedbackSubmission) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "email": row.email,
        "interest": row.interest,
        "found_via": row.found_via,
        "rating": row.rating,
        "suggestion": row.suggestion,
        "mailing_list_opt_in": row.mailing_list_opt_in,
        "session_id": row.session_id,
        "ip_address": row.ip_address,
        "user_agent": row.user_agent,
        "accept_language": row.accept_language,
        "referrer": row.referrer,
        "landing_path": row.landing_path,
        "utm_source": row.utm_source,
        "utm_medium": row.utm_medium,
        "utm_campaign": row.utm_campaign,
        "timezone": row.timezone,
        "screen": row.screen,
        "geo_country": row.geo_country,
        "geo_region": row.geo_region,
        "geo_city": row.geo_city,
        "source": row.source,
        "admin_read": row.admin_read,
        "created_at": to_utc_iso(row.created_at),
    }


async def create_landing_feedback(
    db: AsyncSession,
    *,
    name: str,
    email: str,
    interest: str,
    found_via: Optional[str],
    rating: Optional[int],
    suggestion: str,
    mailing_list_opt_in: bool,
    visitor_meta: dict[str, Any],
) -> LandingFeedbackSubmission:
    row = LandingFeedbackSubmission(
        name=name.strip(),
        email=email.strip().lower(),
        interest=interest.strip(),
        found_via=(found_via or "").strip() or None,
        rating=rating,
        suggestion=(suggestion or "").strip(),
        mailing_list_opt_in=bool(mailing_list_opt_in),
        session_id=visitor_meta.get("session_id"),
        ip_address=visitor_meta.get("ip_address"),
        user_agent=visitor_meta.get("user_agent"),
        accept_language=visitor_meta.get("accept_language"),
        referrer=visitor_meta.get("referrer"),
        landing_path=visitor_meta.get("landing_path"),
        utm_source=visitor_meta.get("utm_source"),
        utm_medium=visitor_meta.get("utm_medium"),
        utm_campaign=visitor_meta.get("utm_campaign"),
        timezone=visitor_meta.get("timezone"),
        screen=visitor_meta.get("screen"),
        geo_country=visitor_meta.get("geo_country"),
        geo_region=visitor_meta.get("geo_region"),
        geo_city=visitor_meta.get("geo_city"),
        source="landing_popup",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def create_landing_visit(
    db: AsyncSession,
    *,
    visitor_meta: dict[str, Any],
) -> Optional[LandingVisit]:
    session_id = (visitor_meta.get("session_id") or "").strip()
    if not session_id:
        return None

    # One beacon per session per ~day — avoid spam from reloads.
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(hours=20)
    existing = (
        await db.execute(
            select(LandingVisit.id)
            .where(LandingVisit.session_id == session_id)
            .where(LandingVisit.created_at >= cutoff)
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        return None

    row = LandingVisit(
        session_id=session_id,
        ip_address=visitor_meta.get("ip_address"),
        user_agent=visitor_meta.get("user_agent"),
        accept_language=visitor_meta.get("accept_language"),
        referrer=visitor_meta.get("referrer"),
        landing_path=visitor_meta.get("landing_path"),
        utm_source=visitor_meta.get("utm_source"),
        utm_medium=visitor_meta.get("utm_medium"),
        utm_campaign=visitor_meta.get("utm_campaign"),
        timezone=visitor_meta.get("timezone"),
        screen=visitor_meta.get("screen"),
        geo_country=visitor_meta.get("geo_country"),
        geo_region=visitor_meta.get("geo_region"),
        geo_city=visitor_meta.get("geo_city"),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def landing_feedback_summary(db: AsyncSession) -> dict:
    total = (
        await db.execute(select(func.count()).select_from(LandingFeedbackSubmission))
    ).scalar_one()
    unread = (
        await db.execute(
            select(func.count())
            .select_from(LandingFeedbackSubmission)
            .where(LandingFeedbackSubmission.admin_read.is_(False))
        )
    ).scalar_one()
    return {"feedback_total": int(total or 0), "feedback_unread": int(unread or 0)}


async def list_landing_feedback(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 200,
) -> list[dict]:
    stmt = select(LandingFeedbackSubmission).order_by(
        LandingFeedbackSubmission.created_at.desc()
    )
    if unread_only:
        stmt = stmt.where(LandingFeedbackSubmission.admin_read.is_(False))
    if search:
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(LandingFeedbackSubmission.name).like(q),
                func.lower(LandingFeedbackSubmission.email).like(q),
                func.lower(LandingFeedbackSubmission.interest).like(q),
                func.lower(LandingFeedbackSubmission.suggestion).like(q),
                func.lower(func.coalesce(LandingFeedbackSubmission.geo_city, "")).like(q),
                func.lower(func.coalesce(LandingFeedbackSubmission.geo_country, "")).like(q),
            )
        )
    stmt = stmt.limit(max(1, min(limit, 500)))
    rows = (await db.execute(stmt)).scalars().all()
    return [feedback_to_dict(row) for row in rows]


async def get_landing_feedback(db: AsyncSession, feedback_id: str) -> Optional[dict]:
    row = (
        await db.execute(
            select(LandingFeedbackSubmission).where(
                LandingFeedbackSubmission.id == feedback_id
            )
        )
    ).scalar_one_or_none()
    return feedback_to_dict(row) if row else None


async def mark_landing_feedback_read(db: AsyncSession, feedback_id: str) -> Optional[dict]:
    row = (
        await db.execute(
            select(LandingFeedbackSubmission).where(
                LandingFeedbackSubmission.id == feedback_id
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    if not row.admin_read:
        row.admin_read = True
        await db.commit()
        await db.refresh(row)
    return feedback_to_dict(row)
