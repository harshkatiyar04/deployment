"""Student dashboard data — pseudonym-first, school-linked progress."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.gamified_persona import get_or_create_persona
from app.chat.models import CircleMember, SponsorCircle
from app.models.enums import Persona
from app.models.school import SchoolStudent
from app.models.signup import SignupRequest
from app.models.student_family import StudentFamilyLink
from app.services.student_family import has_recorded_parental_consent
from app.services.student_pseudonym import pseudonym_meta


@dataclass
class StudentDashboardContext:
    persona: Any
    school_student: Optional[SchoolStudent]
    circle_id: Optional[str]
    circle_name: Optional[str]
    consent: bool


def mask_circle_label(name: Optional[str]) -> str:
    if not name or len(name) < 3:
        return "Your circle"
    return f"{name[0]}*** Circle"


async def resolve_school_student(
    db: AsyncSession,
    signup: SignupRequest,
) -> Optional[SchoolStudent]:
    is_v2 = (signup.onboarding_version or "v1") == "v2"

    link_res = await db.execute(
        select(StudentFamilyLink).where(StudentFamilyLink.student_signup_id == signup.id)
    )
    link = link_res.scalar_one_or_none()
    if link and link.school_student_id:
        res = await db.execute(select(SchoolStudent).where(SchoolStudent.id == link.school_student_id))
        row = res.scalar_one_or_none()
        if row:
            if is_v2 and not row.signup_request_id:
                row.signup_request_id = signup.id
            return row

    res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.signup_request_id == signup.id).limit(1)
    )
    row = res.scalar_one_or_none()
    if row:
        return row

    if not is_v2:
        res = await db.execute(
            select(SchoolStudent).where(SchoolStudent.zenk_id == signup.id).limit(1)
        )
        row = res.scalar_one_or_none()
        if row:
            if not row.signup_request_id:
                row.signup_request_id = signup.id
            return row

        if signup.school_or_college_name and signup.full_name:
            res = await db.execute(
                select(SchoolStudent)
                .where(
                    func.lower(SchoolStudent.full_name) == signup.full_name.strip().lower(),
                    SchoolStudent.grade == (signup.grade_or_year or ""),
                )
                .limit(1)
            )
            return res.scalar_one_or_none()
    return None


async def resolve_student_circle_id(
    db: AsyncSession,
    signup: SignupRequest,
    school_student: Optional[SchoolStudent],
) -> Optional[str]:
    if school_student and school_student.circle_id:
        return school_student.circle_id
    link_res = await db.execute(
        select(StudentFamilyLink).where(StudentFamilyLink.student_signup_id == signup.id)
    )
    link = link_res.scalar_one_or_none()
    if link and link.circle_id:
        return link.circle_id
    if school_student and school_student.circle_id:
        return school_student.circle_id
    mem_res = await db.execute(
        select(CircleMember.circle_id).where(CircleMember.user_id == signup.id).limit(1)
    )
    row = mem_res.scalar_one_or_none()
    return row[0] if row else None


async def load_student_dashboard_context(
    db: AsyncSession,
    signup: SignupRequest,
) -> StudentDashboardContext:
    """Resolve shared student dashboard entities once per request."""
    persona = await get_or_create_persona(signup, db)
    school_student = await resolve_school_student(db, signup)
    circle_id = await resolve_student_circle_id(db, signup, school_student)
    circle_name = None
    if circle_id:
        c_res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
        circle = c_res.scalar_one_or_none()
        circle_name = circle.name if circle else None
    consent = await has_recorded_parental_consent(db, signup.id)
    return StudentDashboardContext(
        persona=persona,
        school_student=school_student,
        circle_id=circle_id,
        circle_name=circle_name,
        consent=consent,
    )


def _profile_from_context(signup: SignupRequest, ctx: StudentDashboardContext) -> dict[str, Any]:
    school_student = ctx.school_student
    return {
        "signup_id": signup.id,
        "pseudonym": ctx.persona.nickname,
        **pseudonym_meta(ctx.persona.nickname),
        "avatar_key": ctx.persona.avatar_key,
        "grade": signup.grade_or_year or (school_student.grade if school_student else None),
        "school_label": "Partner school" if school_student else signup.school_or_college_name,
        "login_access_tier": signup.login_access_tier,
        "has_parental_consent": ctx.consent,
        "kyc_status": signup.kyc_status.value,
        "circle_id": ctx.circle_id,
        "circle_name_masked": mask_circle_label(ctx.circle_name),
        "school_linked": school_student is not None,
        "school_student_id": school_student.id if school_student else None,
    }


async def build_student_profile(
    db: AsyncSession,
    signup: SignupRequest,
    *,
    ctx: Optional[StudentDashboardContext] = None,
) -> dict[str, Any]:
    if ctx is None:
        ctx = await load_student_dashboard_context(db, signup)
    return _profile_from_context(signup, ctx)


async def build_student_overview(
    db: AsyncSession,
    signup: SignupRequest,
    *,
    ctx: Optional[StudentDashboardContext] = None,
) -> dict[str, Any]:
    if ctx is None:
        ctx = await load_student_dashboard_context(db, signup)
    profile = _profile_from_context(signup, ctx)
    school_student = ctx.school_student

    zqa = 0
    attendance = 0
    avg_score = 0
    risk = "—"
    improvement = 0
    school_note = None

    if school_student:
        zqa = int(school_student.zqa_score or 0)
        attendance = int(school_student.attendance_pct or 0)
        avg_score = int(school_student.avg_score or 0)
        risk = school_student.risk_level or "Low"
        improvement = max(0, int(school_student.zqa_baseline_delta or 0))
        if school_student.tutor_recommendation:
            school_note = (school_student.tutor_recommendation or "")[:280]

    member_count = 0
    if profile.get("circle_id"):
        cnt_res = await db.execute(
            select(func.count()).select_from(CircleMember).where(
                CircleMember.circle_id == profile["circle_id"]
            )
        )
        member_count = int(cnt_res.scalar() or 0)

    return {
        **profile,
        "kpis": {
            "zqa_score": zqa,
            "attendance_pct": attendance,
            "avg_score": avg_score,
            "risk_level": risk,
            "improvement_pts": improvement,
            "circle_members": member_count,
        },
        "school_note": school_note,
        "milestones": _milestones(zqa, attendance),
    }


def _milestones(zqa: int, attendance: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if zqa >= 70:
        items.append({"label": "Strong ZQA", "status": "achieved"})
    elif zqa > 0:
        items.append({"label": "Reach ZQA 70", "status": "in_progress"})
    if attendance >= 85:
        items.append({"label": "Attendance champion", "status": "achieved"})
    elif attendance > 0:
        items.append({"label": "85% attendance goal", "status": "in_progress"})
    if not items:
        items.append({"label": "Join your circle & school", "status": "pending"})
    return items


async def build_student_progress(
    db: AsyncSession,
    signup: SignupRequest,
    *,
    quarter: str = "Q4",
    ctx: Optional[StudentDashboardContext] = None,
) -> dict[str, Any]:
    from app.services.sponsor_sponsored_student import build_sponsored_student_profile

    if ctx is None:
        ctx = await load_student_dashboard_context(db, signup)
    school_student = ctx.school_student
    profile = _profile_from_context(signup, ctx)
    if not school_student:
        return {
            "linked": False,
            "pseudonym": profile["pseudonym"],
            "message": "Progress unlocks when your school admits you to your partner school.",
        }

    record = await build_sponsored_student_profile(
        db,
        school_student,
        quarter=quarter,
        viewer="student",
    )
    return {
        "linked": True,
        "quarter": quarter.upper(),
        **record,
    }


async def build_student_circle_view(db: AsyncSession, signup: SignupRequest) -> dict[str, Any]:
    profile = await build_student_profile(db, signup)
    circle_id = profile.get("circle_id")
    if not circle_id:
        return {
            "in_circle": False,
            "message": "Your circle connects when school enrollment is approved.",
        }

    mem_res = await db.execute(
        select(CircleMember, SignupRequest)
        .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
        .where(
            CircleMember.circle_id == circle_id,
            SignupRequest.persona.in_([Persona.sponsor_leader, Persona.sponsor_member, Persona.mentor]),
        )
    )
    members = []
    for idx, (cm, user) in enumerate(mem_res.all()):
        role_label = "Leader" if cm.role in ("lead", "leader") else ("Mentor" if user.persona == Persona.mentor else "Sponsor")
        members.append(
            {
                "masked_name": f"Sponsor #{idx + 1}",
                "role": role_label,
            }
        )

    return {
        "in_circle": True,
        "circle_name_masked": profile["circle_name_masked"],
        "member_count": len(members),
        "members": members[:8],
        "impact_hint": "Your circle supports your learning journey — names stay private for your safety.",
    }


def _normalize_quarter(quarter: str) -> str:
    q = (quarter or "Q4").strip().upper()
    if q not in {"Q1", "Q2", "Q3", "Q4"}:
        return "Q4"
    return q


async def build_student_dashboard_bundle(
    db: AsyncSession,
    signup: SignupRequest,
    *,
    quarter: str = "Q4",
) -> dict[str, Any]:
    """Single round-trip payload for the student dashboard shell."""
    from app.services.student_onboarding_v2 import build_onboarding_timeline

    q = _normalize_quarter(quarter)
    ctx = await load_student_dashboard_context(db, signup)
    profile = _profile_from_context(signup, ctx)
    overview = await build_student_overview(db, signup, ctx=ctx)
    timeline = await build_onboarding_timeline(db, signup, school_student=ctx.school_student)
    progress = await build_student_progress(db, signup, quarter=q, ctx=ctx)
    return {
        "profile": profile,
        "overview": {
            k: overview[k]
            for k in (
                "signup_id",
                "pseudonym",
                "avatar_key",
                "grade",
                "school_label",
                "circle_name_masked",
                "school_linked",
                "kpis",
                "school_note",
                "milestones",
            )
        },
        "timeline": timeline,
        "progress": progress,
    }
