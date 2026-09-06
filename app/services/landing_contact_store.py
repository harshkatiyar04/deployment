"""Persist and query landing-page contact form submissions."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import to_utc_iso
from app.models.landing_contact import LandingContactInquiry

_META_KEYS = (
    "session_id",
    "ip_address",
    "user_agent",
    "accept_language",
    "referrer",
    "landing_path",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "timezone",
    "screen",
    "geo_country",
    "geo_region",
    "geo_city",
)


async def create_landing_contact_inquiry(
    db: AsyncSession,
    *,
    name: str,
    email: str,
    interest: str,
    message: str,
    visitor_meta: Optional[dict[str, Any]] = None,
    source: str = "landing_contact",
) -> LandingContactInquiry:
    meta = visitor_meta or {}
    src = (source or "landing_contact").strip().lower()[:40] or "landing_contact"
    row = LandingContactInquiry(
        name=name.strip(),
        email=email.strip().lower(),
        interest=interest.strip(),
        message=(message or "").strip(),
        source=src,
        **{key: meta.get(key) for key in _META_KEYS},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def mark_inquiry_email_notified(db: AsyncSession, inquiry_id: str) -> None:
    await db.execute(
        update(LandingContactInquiry)
        .where(LandingContactInquiry.id == inquiry_id)
        .values(email_notified=True)
    )
    await db.commit()


async def mark_inquiry_thank_you_sent(db: AsyncSession, inquiry_id: str) -> None:
    await db.execute(
        update(LandingContactInquiry)
        .where(LandingContactInquiry.id == inquiry_id)
        .values(thank_you_sent=True)
    )
    await db.commit()


def inquiry_to_dict(row: LandingContactInquiry) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "email": row.email,
        "interest": row.interest,
        "message": row.message,
        "admin_read": row.admin_read,
        "email_notified": row.email_notified,
        "thank_you_sent": bool(getattr(row, "thank_you_sent", False)),
        "source": getattr(row, "source", None) or "landing_contact",
        "session_id": getattr(row, "session_id", None),
        "ip_address": getattr(row, "ip_address", None),
        "user_agent": getattr(row, "user_agent", None),
        "accept_language": getattr(row, "accept_language", None),
        "referrer": getattr(row, "referrer", None),
        "landing_path": getattr(row, "landing_path", None),
        "utm_source": getattr(row, "utm_source", None),
        "utm_medium": getattr(row, "utm_medium", None),
        "utm_campaign": getattr(row, "utm_campaign", None),
        "timezone": getattr(row, "timezone", None),
        "screen": getattr(row, "screen", None),
        "geo_country": getattr(row, "geo_country", None),
        "geo_region": getattr(row, "geo_region", None),
        "geo_city": getattr(row, "geo_city", None),
        "created_at": to_utc_iso(row.created_at),
    }


async def landing_contact_summary(
    db: AsyncSession,
    *,
    source: Optional[str] = None,
) -> dict:
    base = select(func.count()).select_from(LandingContactInquiry)
    unread_base = (
        select(func.count())
        .select_from(LandingContactInquiry)
        .where(LandingContactInquiry.admin_read.is_(False))
    )
    if source:
        src = source.strip().lower()
        base = base.where(LandingContactInquiry.source == src)
        unread_base = unread_base.where(LandingContactInquiry.source == src)
    total = (await db.execute(base)).scalar_one()
    unread = (await db.execute(unread_base)).scalar_one()
    return {"total": int(total or 0), "unread": int(unread or 0)}


async def list_landing_contact_inquiries(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    unread_only: bool = False,
    source: Optional[str] = None,
    exclude_source: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    stmt = select(LandingContactInquiry).order_by(LandingContactInquiry.created_at.desc())
    if unread_only:
        stmt = stmt.where(LandingContactInquiry.admin_read.is_(False))
    if source:
        stmt = stmt.where(LandingContactInquiry.source == source.strip().lower())
    if exclude_source:
        stmt = stmt.where(LandingContactInquiry.source != exclude_source.strip().lower())
    if search:
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(LandingContactInquiry.name).like(q),
                func.lower(LandingContactInquiry.email).like(q),
                func.lower(LandingContactInquiry.interest).like(q),
                func.lower(LandingContactInquiry.message).like(q),
                func.lower(func.coalesce(LandingContactInquiry.ip_address, "")).like(q),
                func.lower(func.coalesce(LandingContactInquiry.geo_city, "")).like(q),
                func.lower(func.coalesce(LandingContactInquiry.geo_country, "")).like(q),
            )
        )
    stmt = stmt.limit(max(1, min(limit, 500)))
    rows = (await db.execute(stmt)).scalars().all()
    return [inquiry_to_dict(row) for row in rows]


async def get_landing_contact_inquiry(db: AsyncSession, inquiry_id: str) -> Optional[dict]:
    row = (
        await db.execute(
            select(LandingContactInquiry).where(LandingContactInquiry.id == inquiry_id)
        )
    ).scalar_one_or_none()
    return inquiry_to_dict(row) if row else None


async def mark_landing_contact_inquiry_read(db: AsyncSession, inquiry_id: str) -> Optional[dict]:
    row = (
        await db.execute(
            select(LandingContactInquiry).where(LandingContactInquiry.id == inquiry_id)
        )
    ).scalar_one_or_none()
    if not row:
        return None
    if not row.admin_read:
        row.admin_read = True
        await db.commit()
        await db.refresh(row)
    return inquiry_to_dict(row)
