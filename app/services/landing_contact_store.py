"""Persist and query landing-page contact form submissions."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import to_utc_iso
from app.models.landing_contact import LandingContactInquiry


async def create_landing_contact_inquiry(
    db: AsyncSession,
    *,
    name: str,
    email: str,
    interest: str,
    message: str,
) -> LandingContactInquiry:
    row = LandingContactInquiry(
        name=name.strip(),
        email=email.strip().lower(),
        interest=interest.strip(),
        message=(message or "").strip(),
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


def inquiry_to_dict(row: LandingContactInquiry) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "email": row.email,
        "interest": row.interest,
        "message": row.message,
        "admin_read": row.admin_read,
        "email_notified": row.email_notified,
        "created_at": to_utc_iso(row.created_at),
    }


async def landing_contact_summary(db: AsyncSession) -> dict:
    total = (
        await db.execute(select(func.count()).select_from(LandingContactInquiry))
    ).scalar_one()
    unread = (
        await db.execute(
            select(func.count())
            .select_from(LandingContactInquiry)
            .where(LandingContactInquiry.admin_read.is_(False))
        )
    ).scalar_one()
    return {"total": int(total or 0), "unread": int(unread or 0)}


async def list_landing_contact_inquiries(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 200,
) -> list[dict]:
    stmt = select(LandingContactInquiry).order_by(LandingContactInquiry.created_at.desc())
    if unread_only:
        stmt = stmt.where(LandingContactInquiry.admin_read.is_(False))
    if search:
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(LandingContactInquiry.name).like(q),
                func.lower(LandingContactInquiry.email).like(q),
                func.lower(LandingContactInquiry.interest).like(q),
                func.lower(LandingContactInquiry.message).like(q),
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
