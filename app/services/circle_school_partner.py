"""Direct messaging between sponsor circle leaders and partner schools."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.models.school import SchoolProfile, SchoolStudent
from app.models.signup import SignupRequest
from app.services.school_circle_sync import resolve_circle_leader_signup


async def _count_linked_students(
    db: AsyncSession,
    *,
    circle_id: str,
    school_id: str,
) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(SchoolStudent)
        .where(
            SchoolStudent.circle_id == circle_id,
            SchoolStudent.school_id == school_id,
        )
    )
    return int(res.scalar_one() or 0)


async def resolve_school_partner_for_circle(
    db: AsyncSession,
    circle_id: str,
) -> Optional[dict[str, Any]]:
    """Partner school linked via enrolled students in this circle."""
    res = await db.execute(
        select(SchoolStudent, SchoolProfile)
        .join(SchoolProfile, SchoolProfile.id == SchoolStudent.school_id)
        .where(SchoolStudent.circle_id == circle_id)
        .order_by(SchoolStudent.created_at.desc())
        .limit(1)
    )
    row = res.first()
    if not row:
        return None

    _student, profile = row
    leader = await resolve_circle_leader_signup(db, circle_id)
    linked = await _count_linked_students(db, circle_id=circle_id, school_id=profile.id)

    return {
        "school_id": profile.id,
        "school_name": profile.school_name,
        "principal_name": profile.principal_name,
        "city": profile.city,
        "state": profile.district,
        "circle_id": circle_id,
        "linked_students": linked,
        "leader_name": (leader.full_name or "").strip() if leader else None,
    }


async def list_partner_circles_for_school(
    db: AsyncSession,
    school_id: str,
) -> list[dict[str, Any]]:
    """Circles that have at least one student enrolled from this school."""
    res = await db.execute(
        select(
            SchoolStudent.circle_id,
            func.max(SchoolStudent.circle_name).label("circle_name"),
            func.count().label("student_count"),
        )
        .where(
            SchoolStudent.school_id == school_id,
            SchoolStudent.circle_id.isnot(None),
        )
        .group_by(SchoolStudent.circle_id)
        .order_by(func.max(SchoolStudent.created_at).desc())
    )
    rows = res.all()
    out: list[dict[str, Any]] = []
    for circle_id, circle_name, student_count in rows:
        if not circle_id:
            continue
        leader = await resolve_circle_leader_signup(db, circle_id)
        c_res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
        circle = c_res.scalar_one_or_none()
        out.append(
            {
                "circle_id": circle_id,
                "circle_name": circle_name or (circle.name if circle else "Sponsor circle"),
                "leader_name": (leader.full_name or "").strip() if leader else None,
                "linked_students": int(student_count or 0),
            }
        )
    return out


async def fetch_partner_messages(
    db: AsyncSession,
    *,
    circle_id: str,
    school_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    from app.models.circle_ops import CircleSchoolPartnerMessage

    res = await db.execute(
        select(CircleSchoolPartnerMessage)
        .where(
            CircleSchoolPartnerMessage.circle_id == circle_id,
            CircleSchoolPartnerMessage.school_id == school_id,
        )
        .order_by(CircleSchoolPartnerMessage.created_at.asc())
        .limit(limit)
    )
    return [
        {
            "id": m.id,
            "sender_side": m.sender_side,
            "sender_name": m.sender_name,
            "body": m.body,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in res.scalars().all()
    ]


async def post_partner_message(
    db: AsyncSession,
    *,
    circle_id: str,
    school_id: str,
    sender_side: str,
    body: str,
    sender_signup: Optional[SignupRequest] = None,
    sender_name: Optional[str] = None,
) -> dict[str, Any]:
    from app.models.circle_ops import CircleSchoolPartnerMessage

    text = (body or "").strip()
    if not text:
        raise ValueError("Message cannot be empty")

    side = (sender_side or "").lower()
    if side not in ("circle", "school"):
        raise ValueError("Invalid sender side")

    name = (sender_name or "").strip()
    if not name and sender_signup:
        name = (sender_signup.full_name or "User").strip()

    msg = CircleSchoolPartnerMessage(
        circle_id=circle_id,
        school_id=school_id,
        sender_side=side,
        sender_signup_id=sender_signup.id if sender_signup else None,
        sender_name=name or ("Circle leader" if side == "circle" else "School"),
        body=text[:4000],
    )
    db.add(msg)
    await db.flush()
    return {
        "id": msg.id,
        "sender_side": msg.sender_side,
        "sender_name": msg.sender_name,
        "body": msg.body,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
