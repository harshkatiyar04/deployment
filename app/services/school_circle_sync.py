"""Keep school_students circle + sponsor leader fields aligned with live circle data."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.models.school import SchoolStudent
from app.models.signup import SignupRequest

LEADER_ROLES = frozenset({"lead", "coordinator", "sponsor_leader", "sponsor"})


async def resolve_circle_leader_signup(
    db: AsyncSession,
    circle_id: str,
) -> Optional[SignupRequest]:
    res = await db.execute(
        select(CircleMember, SignupRequest)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(CircleMember.circle_id == circle_id)
        .order_by(CircleMember.joined_at.asc())
    )
    leader: Optional[SignupRequest] = None
    for cm, signup in res.all():
        role = (cm.role or "").lower()
        if role in LEADER_ROLES:
            if role in ("sponsor_leader", "lead", "coordinator"):
                return signup
            if leader is None:
                leader = signup
    return leader


async def sync_school_student_circle_link(
    db: AsyncSession,
    school_student: SchoolStudent,
    circle_id: str,
    *,
    leader: Optional[SignupRequest] = None,
    force_sl: bool = True,
) -> dict[str, Any]:
    """Update circle_id/name and SL from the linked sponsor circle."""
    c_res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
    circle = c_res.scalar_one_or_none()
    if not circle:
        return {"synced": False, "reason": "circle_not_found"}

    school_student.circle_id = circle_id
    school_student.circle_name = circle.name

    if leader is None:
        leader = await resolve_circle_leader_signup(db, circle_id)

    sl_name = None
    if leader:
        sl_name = (leader.full_name or "").strip() or None
        if force_sl or not school_student.sl_name:
            school_student.sl_name = sl_name

    return {
        "synced": True,
        "circle_id": circle_id,
        "circle_name": circle.name,
        "sl_name": school_student.sl_name,
        "leader_signup_id": leader.id if leader else None,
    }


async def backfill_circle_links_for_school(
    db: AsyncSession,
    school_id: str,
) -> dict[str, Any]:
    res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.school_id == school_id,
            SchoolStudent.circle_id.isnot(None),
        )
    )
    students = list(res.scalars().all())
    updated = 0
    for student in students:
        if not student.circle_id:
            continue
        out = await sync_school_student_circle_link(db, student, student.circle_id)
        if out.get("synced"):
            updated += 1
    return {"students_checked": len(students), "students_updated": updated}
