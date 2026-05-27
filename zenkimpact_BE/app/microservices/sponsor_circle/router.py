from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import get_current_user, get_optional_current_user
from app.db.session import get_db
from app.chat.models import CircleMember, SponsorCircle
from app.models.school import SchoolProfile, SchoolStudentEnrollmentRequest
from app.models.signup import SignupRequest
from app.microservices.school.schemas import (
    SchoolEnrollmentRequestResponse,
    CircleEnrollmentReviewRequest,
    CircleEnrollmentRejectRequest,
    SchoolStudentResponse,
)
from app.services.school_student_enrollment import (
    approve_enrollment_request,
    reject_enrollment_request,
    enrollment_request_to_dict,
    ENROLLMENT_PENDING,
)
from app.microservices.sponsor_circle.schemas import (
    SummaryResponse,
    BudgetResponse,
    SetCircleBudgetRequest,
    ParticipationResponse,
    Member,
    StudentUpdateResponse,
    TimeImpactResponse,
    RankingsResponse,
    CircleRankRow,
    KiaInsightResponse,
)
from app.services.kia import generate_budget_insight
from app.services.circle_budget import (
    build_budget_payload,
    resolve_user_circle,
    set_circle_budget,
    DEFAULT_TXNS,
)
from app.services.demo_circle import (
    DEMO_CIRCLE_ID,
    ensure_user_in_demo_circle,
)

router = APIRouter(prefix="/sponsor-circle", tags=["Sponsor Circle Dashboard"])


@router.get("/summary", response_model=SummaryResponse)
async def get_summary():
    return SummaryResponse(
        zenq_score=82,
        circle_rank=3,
        total_circles=47,
        participation_pct=74,
        circle_avg_pct=68,
        time_this_month_hrs=6.5,
        top_group_hrs=11.2,
        zenq_change=4,
        rank_previous=5,
    )


def _default_budget_data() -> dict:
    return {
        "circle_id": None,
        "circle_name": None,
        "total_budget": 150_000,
        "spent": 94_200,
        "collected": 124_500,
        "balance_to_spend": 55_800,
        "fy_label": "FY 2025-26",
        "fy_key": "2025-26",
        "transactions": DEFAULT_TXNS,
        "can_set_budget": False,
        "budget_set_at": None,
    }


@router.get("/budget", response_model=BudgetResponse)
async def get_budget(
    circle_id: Optional[str] = None,
    user: Optional[SignupRequest] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = _default_budget_data()
    if user:
        try:
            circle, role = await resolve_user_circle(db, user.id, circle_id)
            data = build_budget_payload(circle, role)
        except HTTPException:
            pass
    return BudgetResponse(**data)


@router.put("/budget", response_model=BudgetResponse)
async def update_budget(
    body: SetCircleBudgetRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Circle leader sets the annual budget for the current FY."""
    data = await set_circle_budget(
        db,
        user,
        body.annual_budget,
        fy_label=body.fy_label,
        circle_id=body.circle_id,
    )
    return BudgetResponse(**data)


@router.get("/participation", response_model=ParticipationResponse)
async def get_participation():
    return ParticipationResponse(
        members=[
            Member(name="Rohit Chawla", initials="RC", participation_pct=94, badge="top"),
            Member(name="Priya Sharma", initials="PS", participation_pct=74, badge="you"),
            Member(name="Arjun Kulkarni", initials="AK", participation_pct=70, badge=""),
            Member(name="Sneha Mehta", initials="SM", participation_pct=64, badge=""),
            Member(name="Vikram Patil", initials="VP", participation_pct=60, badge=""),
            Member(name="Mrs. Devika", initials="MD", participation_pct=46, badge=""),
        ],
        circle_avg_pct=68,
        leader_name="Rohit Chawla",
        leader_pct=94,
    )


@router.get("/student-update", response_model=StudentUpdateResponse)
async def get_student_update():
    return StudentUpdateResponse(
        student_name="Ananya D.",
        maths_score=84,
        maths_baseline=61,
        science_score=78,
        science_baseline=55,
        attendance_pct=92,
        improvement_pts=23,
        school_comment="Ananya is asking about entering a district-level science competition. Excellent engagement this term.",
    )


@router.get("/time-impact", response_model=TimeImpactResponse)
async def get_time_impact():
    return TimeImpactResponse(
        total_hrs_all_circles=847,
        total_circles_count=47,
        highest_circle_hrs=11.2,
        highest_circle_name="Vasundhara Circle, Pune",
        my_circle_hrs=6.5,
    )


@router.get("/rankings", response_model=RankingsResponse)
async def get_rankings():
    return RankingsResponse(
        circles=[
            CircleRankRow(rank=1, name="Vasundhara Circle", zenq=96, city="Pune", is_mine=False),
            CircleRankRow(rank=2, name="Prarambh Mumbai", zenq=89, city="Mumbai", is_mine=False),
            CircleRankRow(rank=3, name="Ashoka Rising", zenq=82, city="Mumbai", is_mine=True),
            CircleRankRow(rank=4, name="Udaan Bangalore", zenq=78, city="Bengaluru", is_mine=False),
            CircleRankRow(rank=5, name="Kishore Circle", zenq=71, city="Delhi", is_mine=False),
        ]
    )


@router.get("/budget-insight", response_model=KiaInsightResponse)
async def get_budget_insight(
    user: Optional[SignupRequest] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    budget_data = _default_budget_data()
    if user:
        try:
            circle, role = await resolve_user_circle(db, user.id)
            budget_data = build_budget_payload(circle, role)
        except HTTPException:
            pass

    insight = await generate_budget_insight(budget_data)
    
    return KiaInsightResponse(
        analysis=insight.get("analysis", ""),
        suggestion=insight.get("suggestion", ""),
        coordinator_name=insight.get("coordinator_name", "Rohit")
    )


@router.get("/my-circles")
async def get_my_circles(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Circles the logged-in user belongs to (for enrollment review)."""
    res = await db.execute(
        select(SponsorCircle, CircleMember.role)
        .join(CircleMember, CircleMember.circle_id == SponsorCircle.id)
        .where(CircleMember.user_id == user.id)
        .order_by(SponsorCircle.name)
    )
    return [
        {"id": row[0].id, "name": row[0].name, "role": row[1]}
        for row in res.all()
    ]


@router.post("/join-demo-circle")
async def join_demo_circle(
    as_leader: bool = False,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dev helper: enroll the logged-in sponsor in the demo circle so chat WebSockets work.
    """
    persona = str(user.persona or "").lower()
    if persona not in ("sponsor", "sponsor_leader", "sponsor_member", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Only sponsor accounts can join the demo circle.",
        )
    role = "sponsor_leader" if as_leader else "sponsor"
    await ensure_user_in_demo_circle(db, user.id, role=role)
    return {
        "id": DEMO_CIRCLE_ID,
        "name": "Ashoka Rising (Demo)",
        "role": role,
    }


@router.get("/enrollment-requests", response_model=List[SchoolEnrollmentRequestResponse])
async def list_circle_enrollment_requests(
    circle_id: Optional[str] = None,
    status: Optional[str] = ENROLLMENT_PENDING,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pending school enrollment intimations for the user's circle(s)."""
    member_res = await db.execute(
        select(CircleMember.circle_id).where(CircleMember.user_id == user.id)
    )
    circle_ids = [r[0] for r in member_res.all()]
    if not circle_ids:
        return []

    if circle_id:
        if circle_id not in circle_ids:
            raise HTTPException(status_code=403, detail="Not a member of this circle.")
        circle_ids = [circle_id]

    q = select(SchoolStudentEnrollmentRequest).where(
        SchoolStudentEnrollmentRequest.circle_id.in_(circle_ids)
    )
    if status:
        q = q.where(SchoolStudentEnrollmentRequest.status == status)
    q = q.order_by(SchoolStudentEnrollmentRequest.requested_at.desc())

    res = await db.execute(q)
    rows = res.scalars().all()
    school_names: dict[str, str] = {}
    out = []
    for req in rows:
        if req.school_id not in school_names:
            prof = await db.execute(
                select(SchoolProfile.school_name).where(SchoolProfile.id == req.school_id)
            )
            school_names[req.school_id] = prof.scalar_one_or_none() or "School"
        out.append(
            SchoolEnrollmentRequestResponse(
                **enrollment_request_to_dict(req, school_name=school_names[req.school_id])
            )
        )
    return out


@router.post("/enrollment-requests/{request_id}/approve", response_model=SchoolStudentResponse)
async def approve_circle_enrollment(
    request_id: str,
    body: CircleEnrollmentReviewRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        student = await approve_enrollment_request(
            db, request_id=request_id, user=user, review_note=body.review_note
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return SchoolStudentResponse(
        id=student.id,
        full_name=student.full_name,
        grade=student.grade,
        circle_id=student.circle_id,
        circle_name=student.circle_name,
        attendance_pct=student.attendance_pct,
        avg_score=student.avg_score,
        zqa_score=student.zqa_score,
        risk_level=student.risk_level,
        q_report_status=student.q_report_status,
        tutor_recommendation=student.tutor_recommendation,
        tutor_recommendation_status=student.tutor_recommendation_status,
        zenk_id=student.zenk_id,
        dob=student.dob,
        class_teacher=student.class_teacher,
        sl_name=student.sl_name,
        mentor_name=student.mentor_name,
        rank_in_class=student.rank_in_class,
        class_size=student.class_size,
        zenq_contribution=student.zenq_contribution,
        zqa_baseline_delta=student.zqa_baseline_delta,
    )


@router.post("/enrollment-requests/{request_id}/reject", response_model=SchoolEnrollmentRequestResponse)
async def reject_circle_enrollment(
    request_id: str,
    body: CircleEnrollmentRejectRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        req = await reject_enrollment_request(
            db, request_id=request_id, user=user, review_note=body.review_note
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    prof_res = await db.execute(
        select(SchoolProfile.school_name).where(SchoolProfile.id == req.school_id)
    )
    school_name = prof_res.scalar_one_or_none()
    return SchoolEnrollmentRequestResponse(
        **enrollment_request_to_dict(req, school_name=school_name)
    )
