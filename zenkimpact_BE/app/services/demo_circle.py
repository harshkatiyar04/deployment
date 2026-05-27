"""Dev demo circle — fixed ID used by sponsor / leader dashboards."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatChannel, CircleMember, SponsorCircle

DEMO_CIRCLE_ID = "4498c25e-b3f4-4f65-a2f4-bc8a235d36d9"
DEMO_CIRCLE_NAME = "Ashoka Rising (Demo)"


async def ensure_demo_circle_row(db: AsyncSession) -> SponsorCircle:
    res = await db.execute(
        select(SponsorCircle).where(SponsorCircle.id == DEMO_CIRCLE_ID)
    )
    circle = res.scalar_one_or_none()
    if circle:
        return circle

    circle = SponsorCircle(
        id=DEMO_CIRCLE_ID,
        name=DEMO_CIRCLE_NAME,
        description="Demo circle for sponsor / leader dashboards and chat.",
        status="active",
    )
    db.add(circle)
    await db.flush()

    channel_res = await db.execute(
        select(ChatChannel).where(
            ChatChannel.circle_id == DEMO_CIRCLE_ID,
            ChatChannel.name == "general",
        )
    )
    if not channel_res.scalar_one_or_none():
        db.add(
            ChatChannel(
                circle_id=DEMO_CIRCLE_ID,
                name="general",
                channel_type="persistent",
            )
        )
    return circle


async def ensure_user_in_demo_circle(
    db: AsyncSession,
    user_id: str,
    *,
    role: str = "sponsor",
) -> CircleMember:
    await ensure_demo_circle_row(db)
    res = await db.execute(
        select(CircleMember).where(
            CircleMember.circle_id == DEMO_CIRCLE_ID,
            CircleMember.user_id == user_id,
        )
    )
    member = res.scalar_one_or_none()
    if member:
        return member

    member = CircleMember(
        circle_id=DEMO_CIRCLE_ID,
        user_id=user_id,
        role=role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member
