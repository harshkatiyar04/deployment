"""Live platform user registry for admin (no placeholders)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.models.enums import KycStatus, Persona
from app.models.mentor import MentorProfile
from app.models.refresh_token import RefreshToken
from app.models.school import SchoolStudent
from app.models.signup import SignupRequest

LEADER_ROLES = frozenset({"lead", "sponsor_leader", "coordinator", "leader"})

PERSONA_LABELS = {
    Persona.sponsor: "Sponsor",
    Persona.sponsor_leader: "Sponsor leader",
    Persona.sponsor_member: "Sponsor member",
    Persona.vendor: "Vendor",
    Persona.student: "Student",
    Persona.corporate: "Corporate",
    Persona.mentor: "Mentor",
    Persona.school: "School",
}


def _persona_value(p: Persona | str) -> str:
    return p.value if hasattr(p, "value") else str(p)


def _kyc_value(s: KycStatus | str) -> str:
    return s.value if hasattr(s, "value") else str(s)


def _account_status(kyc: KycStatus) -> str:
    if kyc == KycStatus.approved:
        return "active"
    if kyc in (KycStatus.pending, KycStatus.info_required):
        return "pending"
    return "suspended"


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def build_admin_users_registry(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    persona: Optional[str] = None,
    status: Optional[str] = None,
) -> dict[str, Any]:
    users_res = await db.execute(
        select(SignupRequest)
        .where(SignupRequest.email != "admin@zenk")
        .order_by(SignupRequest.created_at.desc())
    )
    users = list(users_res.scalars().all())
    user_ids = [u.id for u in users]

    membership_rows: dict[str, list[tuple]] = {uid: [] for uid in user_ids}
    if user_ids:
        mem_res = await db.execute(
            select(
                CircleMember.user_id,
                CircleMember.role,
                SponsorCircle.id,
                SponsorCircle.name,
                SponsorCircle.budget_collected,
                SponsorCircle.budget_spent,
            )
            .join(SponsorCircle, SponsorCircle.id == CircleMember.circle_id)
            .where(CircleMember.user_id.in_(user_ids))
        )
        for uid, role, cid, cname, collected, spent in mem_res.all():
            membership_rows.setdefault(uid, []).append(
                (role, cid, cname, collected or 0, spent or 0)
            )

    mentor_map: dict[str, MentorProfile] = {}
    if user_ids:
        mentor_res = await db.execute(
            select(MentorProfile).where(MentorProfile.id.in_(user_ids))
        )
        mentor_map = {m.id: m for m in mentor_res.scalars().all()}

    circle_ids = {
        row[1]
        for rows in membership_rows.values()
        for row in rows
    }
    zenq_by_circle: dict[str, int] = {}
    if circle_ids:
        zq_res = await db.execute(
            select(
                SchoolStudent.circle_id,
                func.avg(SchoolStudent.zqa_score),
                func.count(SchoolStudent.id),
            )
            .where(
                SchoolStudent.circle_id.in_(circle_ids),
                SchoolStudent.zqa_score.isnot(None),
            )
            .group_by(SchoolStudent.circle_id)
        )
        for cid, avg_score, _cnt in zq_res.all():
            if avg_score is not None:
                zenq_by_circle[cid] = int(round(float(avg_score)))

    member_count_by_circle: dict[str, int] = {}
    if circle_ids:
        cnt_res = await db.execute(
            select(CircleMember.circle_id, func.count())
            .where(CircleMember.circle_id.in_(circle_ids))
            .group_by(CircleMember.circle_id)
        )
        member_count_by_circle = {cid: int(n) for cid, n in cnt_res.all()}

    leader_circle_by_user: dict[str, SponsorCircle] = {}
    if user_ids:
        lc_res = await db.execute(
            select(SponsorCircle)
            .where(SponsorCircle.budget_set_by.in_(user_ids))
            .order_by(SponsorCircle.created_at.desc())
        )
        for circle in lc_res.scalars().all():
            if circle.budget_set_by and circle.budget_set_by not in leader_circle_by_user:
                leader_circle_by_user[circle.budget_set_by] = circle

    extra_circle_ids = {c.id for c in leader_circle_by_user.values()} - circle_ids
    if extra_circle_ids:
        zq_extra = await db.execute(
            select(SchoolStudent.circle_id, func.avg(SchoolStudent.zqa_score))
            .where(
                SchoolStudent.circle_id.in_(extra_circle_ids),
                SchoolStudent.zqa_score.isnot(None),
            )
            .group_by(SchoolStudent.circle_id)
        )
        for cid, avg_score in zq_extra.all():
            if avg_score is not None:
                zenq_by_circle[cid] = int(round(float(avg_score)))
        mc_extra = await db.execute(
            select(CircleMember.circle_id, func.count())
            .where(CircleMember.circle_id.in_(extra_circle_ids))
            .group_by(CircleMember.circle_id)
        )
        for cid, n in mc_extra.all():
            member_count_by_circle[cid] = int(n)

    last_active: dict[str, datetime] = {}
    if user_ids:
        la_res = await db.execute(
            select(RefreshToken.user_id, func.max(RefreshToken.created_at))
            .where(RefreshToken.user_id.in_(user_ids))
            .group_by(RefreshToken.user_id)
        )
        last_active = {uid: ts for uid, ts in la_res.all() if ts}

    def pick_membership(uid: str) -> Optional[tuple]:
        rows = membership_rows.get(uid) or []
        if not rows:
            return None
        for row in rows:
            if (row[0] or "").lower() in LEADER_ROLES:
                return row
        return rows[0]

    items: list[dict[str, Any]] = []
    for u in users:
        if u.email == "kia@zenk.ai":
            continue

        mem = pick_membership(u.id)
        circle_id = mem[1] if mem else None
        circle_role = mem[0] if mem else None
        circle_name = mem[2] if mem else None
        is_leader = (
            (circle_role or "").lower() in LEADER_ROLES if circle_role else False
        ) or u.persona == Persona.sponsor_leader
        collected = mem[3] if mem else None
        spent = mem[4] if mem else None

        if is_leader and not circle_id:
            lead_circle = leader_circle_by_user.get(u.id)
            if lead_circle:
                circle_id = lead_circle.id
                circle_name = lead_circle.name
                collected = lead_circle.budget_collected or 0
                spent = lead_circle.budget_spent or 0

        mentor = mentor_map.get(u.id)
        zenq_score = zenq_by_circle.get(circle_id) if circle_id else None

        item = {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "mobile": u.mobile,
            "persona": _persona_value(u.persona),
            "persona_label": PERSONA_LABELS.get(u.persona, _persona_value(u.persona)),
            "kyc_status": _kyc_value(u.kyc_status),
            "status": _account_status(u.kyc_status),
            "circle_id": circle_id,
            "circle_name": circle_name,
            "circle_role": circle_role,
            "is_circle_leader": is_leader,
            "zenq_score": zenq_score,
            "inspire_index": round(float(mentor.inspire_index), 1) if mentor else None,
            "zenq_contribution": round(float(mentor.zenq_contribution), 1) if mentor else None,
            "group_contribution_inr": int(collected) if is_leader and collected else None,
            "circle_spend_inr": int(spent) if is_leader and spent else None,
            "circle_member_count": member_count_by_circle.get(circle_id) if circle_id else None,
            "joined_at": _iso(u.created_at),
            "last_active_at": _iso(last_active.get(u.id) or u.updated_at),
        }
        items.append(item)

    needle = (search or "").strip().lower()
    if needle:
        items = [
            i
            for i in items
            if needle in (i["full_name"] or "").lower()
            or needle in (i["email"] or "").lower()
            or needle in (i["circle_name"] or "").lower()
        ]

    if persona and persona != "all":
        items = [i for i in items if i["persona"] == persona]

    if status and status != "all":
        items = [i for i in items if i["status"] == status]

    summary = {
        "total": len(items),
        "active": sum(1 for i in items if i["status"] == "active"),
        "pending": sum(1 for i in items if i["status"] == "pending"),
        "suspended": sum(1 for i in items if i["status"] == "suspended"),
        "leaders": sum(1 for i in items if i["is_circle_leader"]),
    }

    return {"summary": summary, "users": items}
