"""Real profile pulse feed for sponsor dashboards (no mock stories)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.models.school import SchoolStudent, SchoolStudentEnrollmentRequest
from app.models.signup import SignupRequest
from app.services.impact_briefing import build_briefing_feed_for_circle
from app.services.school_enrollment_constants import ENROLLMENT_PENDING
from app.services.sponsor_circle_finance import fetch_circle_orders
from app.services.sponsor_gamification import compute_sponsor_gamification
from app.services.student_circle_privacy import (
    display_name_for_roster,
    is_beneficiary_role,
    mask_student_for_circle,
)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


async def build_profile_pulse(db: AsyncSession, circle: SponsorCircle, user: SignupRequest) -> dict:
    items: list[dict] = []

    enroll_res = await db.execute(
        select(SchoolStudentEnrollmentRequest)
        .where(
            SchoolStudentEnrollmentRequest.circle_id == circle.id,
            SchoolStudentEnrollmentRequest.status == ENROLLMENT_PENDING,
        )
        .order_by(SchoolStudentEnrollmentRequest.requested_at.desc())
        .limit(5)
    )
    for req in enroll_res.scalars().all():
        items.append(
            {
                "id": f"enroll-{req.id}",
                "type": "CIRCLE",
                "text": f"School enrollment pending: {req.full_name} ({req.grade})",
                "source": "School Comm",
                "time": _iso(req.requested_at),
            }
        )

    student_res = await db.execute(
        select(SchoolStudent)
        .where(SchoolStudent.circle_id == circle.id)
        .order_by(SchoolStudent.created_at.desc())
        .limit(5)
    )
    for st in student_res.scalars().all():
        if st.zqa_score and st.zqa_score > 0:
            masked = await mask_student_for_circle(db, st)
            items.append(
                {
                    "id": f"student-zqa-{st.id}",
                    "type": "CIRCLE",
                    "text": (
                        f"{masked['pseudonym']}: ZQA {int(st.zqa_score)}, "
                        f"attendance {int(st.attendance_pct or 0)}%"
                    ),
                    "source": "Student records",
                    "time": _iso(st.created_at),
                }
            )

    member_res = await db.execute(
        select(CircleMember, SignupRequest)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(CircleMember.circle_id == circle.id)
        .order_by(CircleMember.joined_at.desc())
        .limit(5)
    )
    for cm, signup in member_res.all():
        if signup.id == user.id or is_beneficiary_role(cm.role):
            continue
        display_name, _, _ = await display_name_for_roster(
            db, signup, cm_role=cm.role or ""
        )
        items.append(
            {
                "id": f"member-{signup.id}",
                "type": "CIRCLE",
                "text": f"{display_name} joined the circle",
                "source": "Membership",
                "time": _iso(cm.joined_at),
            }
        )

    for order, pname in (await fetch_circle_orders(db, circle))[:5]:
        amt = int(round(float(order.total_amount or 0)))
        items.append(
            {
                "id": f"order-{order.id}",
                "type": "CIRCLE",
                "text": f"Order: {pname or 'item'} — ₹{amt:,} ({order.order_type})",
                "source": "Marketplace",
                "time": _iso(order.created_at),
            }
        )

    items.sort(key=lambda x: x.get("time") or "", reverse=True)

    briefing = await build_briefing_feed_for_circle(db, circle)
    global_feed = [
        {
            "id": f"brief-{n['id']}",
            "type": n.get("type") or "BRIEFING",
            "text": n["text"],
            "summary": n.get("summary") or n["text"],
            "source": n.get("source") or "Impact Briefing",
            "time": n.get("time"),
            "image": n.get("image"),
            "url": n.get("url") or "",
            "category": n.get("category"),
        }
        for n in briefing.get("items") or []
    ]

    gamification = await compute_sponsor_gamification(db, circle=circle, user=user)

    return {
        "circle_feed": items[:12],
        "global_feed": global_feed,
        "global_available": bool(global_feed),
        "global_news_status": briefing.get("status"),
        "global_news_message": briefing.get("message"),
        "global_news_stale": briefing.get("stale", False),
        "badges": gamification["badges"],
        "badges_available": gamification["badges_available"],
        "badges_earned_count": gamification["badges_earned_count"],
        "badges_total": gamification["badges_total"],
        "streaks": gamification["streaks"],
    }


async def build_circle_students(db: AsyncSession, circle_id: str) -> list[dict]:
    from app.services.student_circle_privacy import mask_student_for_circle

    res = await db.execute(
        select(SchoolStudent)
        .where(SchoolStudent.circle_id == circle_id)
        .order_by(SchoolStudent.full_name)
    )
    rows = []
    for s in res.scalars().all():
        masked = await mask_student_for_circle(db, s)
        pseudonym = masked["pseudonym"]
        initials = "".join(p[0] for p in pseudonym.replace("_", " ").split()[:2]).upper() or "?"
        rows.append(
            {
                "id": s.id,
                "name": pseudonym,
                "pseudonym": pseudonym,
                "grade": s.grade,
                "attendance_pct": int(s.attendance_pct or 0),
                "zqa_score": int(s.zqa_score or 0) if s.zqa_score else None,
                "initials": initials,
            }
        )
    return rows
