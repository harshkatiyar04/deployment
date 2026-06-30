from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import get_current_user
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
from app.services.school_enrollment_constants import ENROLLMENT_PENDING
from app.services.school_student_enrollment import (
    approve_enrollment_request,
    reject_enrollment_request,
    enrollment_request_to_dict,
)
from app.microservices.sponsor_circle.schemas import (
    SummaryResponse,
    BudgetResponse,
    SetCircleBudgetRequest,
    ProvisionCircleRequest,
    ParticipationResponse,
    SponsoredStudentSummary,
    Member,
    StudentUpdateResponse,
    SponsoredStudentProfileResponse,
    TimeImpactResponse,
    RankingsResponse,
    CircleRankRow,
    KiaInsightResponse,
    PendingCircleMembersResponse,
    PendingCircleMemberItem,
    MemberApplicationDecisionRequest,
    PatchCircleNameRequest,
    CircleOverviewResponse,
    CircleInviteLinkResponse,
    InviteResolveResponse,
    StudentCartSubmitRequest,
    StudentCartSubmissionOut,
    StudentCartDecisionRequest,
    StatementResponse,
    VendorPaymentRow,
    VendorPaymentsDashboardResponse,
    CirclePayeeResponse,
    CirclePayeeCreateRequest,
    DisbursementHistoryRow,
    DepositRequestAlert,
    InitiateDisbursementRequest,
    InitiateDisbursementResponse,
    CompleteDisbursementRequest,
    MemberContributionsResponse,
    MemberContributionRow,
    ProfilePulseResponse,
    SponsorBadge,
    SponsorStreak,
    PulseItem,
    ImpactLeagueResponse,
    ImpactLeagueRow,
    ImpactImprovementResponse,
    CircleStudentRow,
    SchoolPartnerResponse,
    SchoolPartnerMessage,
    SchoolPartnerMessageRequest,
    MemberRemovalRequestBody,
    MemberLimitRequestBody,
    CircleRenameRequestBody,
    CircleRenameStatusOut,
    CircleAdminRequestOut,
    CircleAdminRequestCreateResponse,
)
from app.services.circle_membership_ops import (
    assert_can_add_member,
    list_circle_admin_requests,
    request_member_limit_increase,
    request_member_removal,
    request_to_dict,
)
from app.services.sponsor_circle_finance import (
    build_statement,
    build_vendor_payments,
    build_member_contributions,
    compute_spent_from_orders,
    orders_to_budget_transactions,
    fetch_circle_orders,
)
from app.services.sponsor_circle_pulse import build_profile_pulse, build_circle_students
from app.services.sponsor_circle_overview import build_circle_overview
from app.services.sponsor_circle_impact import build_impact_improvement
from app.services.sponsor_circle_time_impact import build_time_impact, build_member_participation
from app.services.circle_invite_token import (
    create_circle_invite_token,
    resolve_invite_token,
)
from app.services.circle_student_cart import (
    submit_student_cart,
    list_pending_carts,
    decide_student_cart,
)
from app.services.kia import generate_budget_insight
from app.services.circle_budget import (
    build_budget_payload,
    resolve_user_circle,
    set_circle_budget,
    _can_set_budget,
)
from app.models.enums import KycStatus, Persona
from app.services.circle_provision import provision_leader_circle
from app.core.settings import settings
from app.services.demo_circle import (
    DEMO_CIRCLE_ID,
    ensure_user_in_demo_circle,
)

router = APIRouter(prefix="/sponsor-circle", tags=["Sponsor Circle Dashboard"])


@router.get("/overview", response_model=CircleOverviewResponse)
async def get_circle_overview(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    try:
        data = await build_circle_overview(db, user.id, circle.id)
    except ValueError:
        raise HTTPException(status_code=403, detail="Not a member of this circle.") from None
    return CircleOverviewResponse(**data)


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Legacy shape — backed by live overview when user has a circle."""
    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    try:
        ov = await build_circle_overview(db, user.id, circle.id)
    except ValueError:
        raise HTTPException(status_code=403, detail="Not a member of this circle.") from None
    return SummaryResponse(
        zenq_score=int(ov["zenq_score"] or 0),
        circle_rank=int(ov["circle_rank"] or 0),
        total_circles=int(ov["total_circles"] or 0),
        participation_pct=int(ov["participation_pct"] or 0),
        circle_avg_pct=int(ov["circle_avg_pct"] or 0),
        time_this_month_hrs=float(ov["time_this_month_hrs"] or 0),
        top_group_hrs=float(ov["top_group_hrs"] or 0),
        zenq_change=int(ov["zenq_change"] or 0),
        rank_previous=int(ov["rank_previous"] or 0),
    )


async def _budget_payload_for_circle(db: AsyncSession, circle: SponsorCircle, role: str) -> dict:
    rows = await fetch_circle_orders(db, circle)
    spent = sum(int(round(float(o.total_amount or 0))) for o, _ in rows)
    txns = orders_to_budget_transactions(rows)
    return build_budget_payload(circle, role, spent=spent, transactions=txns)


@router.get("/budget", response_model=BudgetResponse)
async def get_budget(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, role = await resolve_user_circle(db, user.id, circle_id)
    data = await _budget_payload_for_circle(db, circle, role)
    if user.persona == Persona.sponsor_leader:
        data["can_set_budget"] = True
    return BudgetResponse(**data)


from app.services.circle_member_invite import (
    LEADER_APPROVED,
    LEADER_PENDING,
    LEADER_REJECTED,
    build_invite_note,
    invite_tag_for_query,
    parse_invite_note,
)
from app.services.notifications import notify_user_leader_circle_decision


def _invite_note_filter(circle_id: str):
    tag = invite_tag_for_query(circle_id)
    return or_(
        SignupRequest.admin_note == tag,
        SignupRequest.admin_note.like(f"{tag}|%"),
    )


async def _member_in_circle(db: AsyncSession, circle_id: str, user_id: str) -> bool:
    res = await db.execute(
        select(CircleMember.id).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == user_id,
        )
    )
    return res.scalar_one_or_none() is not None


@router.get("/pending-member-signups", response_model=PendingCircleMembersResponse)
async def list_pending_member_signups(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Leaders only: signups that used this circle's invite link."""
    if user.persona != Persona.sponsor_leader:
        raise HTTPException(status_code=403, detail="Not authorized to view member applications.")
    circle, role = await resolve_user_circle(db, user.id, circle_id)
    if not _can_set_budget(role):
        raise HTTPException(
            status_code=403,
            detail="Only circle leaders can view pending member applications.",
        )

    res = await db.execute(
        select(SignupRequest)
        .where(
            SignupRequest.persona == Persona.sponsor_member,
            _invite_note_filter(circle.id),
        )
        .order_by(SignupRequest.created_at.desc())
    )
    rows = res.scalars().all()
    items: list[PendingCircleMemberItem] = []
    for r in rows:
        _cid, leader_status = parse_invite_note(r.admin_note)
        if _cid and _cid != circle.id:
            continue
        kyc = r.kyc_status.value if hasattr(r.kyc_status, "value") else str(r.kyc_status)
        in_circle = await _member_in_circle(db, circle.id, r.id)
        if in_circle:
            leader_status = LEADER_APPROVED
        can_decide = (
            leader_status == LEADER_PENDING
            and not in_circle
            and kyc == KycStatus.approved.value
        )
        items.append(
            PendingCircleMemberItem(
                id=r.id,
                full_name=r.full_name,
                email=r.email,
                kyc_status=kyc,
                leader_status=leader_status,
                in_circle=in_circle,
                can_approve=can_decide,
                can_reject=leader_status == LEADER_PENDING and not in_circle,
                created_at=r.created_at,
            )
        )
    return PendingCircleMembersResponse(
        circle_id=circle.id,
        circle_name=circle.name,
        members=items,
    )


@router.post("/member-applications/{signup_id}/decision")
async def decide_member_application(
    signup_id: str,
    body: MemberApplicationDecisionRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Circle leader approves or rejects a member who applied via invite link."""
    if user.persona != Persona.sponsor_leader:
        raise HTTPException(status_code=403, detail="Only circle leaders may approve member applications.")
    decision = (body.decision or "").strip().lower()
    if decision not in (LEADER_APPROVED, LEADER_REJECTED):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")

    circle, role = await resolve_user_circle(db, user.id, body.circle_id)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can decide member applications.")

    res = await db.execute(select(SignupRequest).where(SignupRequest.id == signup_id))
    applicant = res.scalar_one_or_none()
    if not applicant or applicant.persona != Persona.sponsor_member:
        raise HTTPException(status_code=404, detail="Member application not found.")

    invite_cid, leader_status = parse_invite_note(applicant.admin_note)
    if invite_cid != circle.id:
        raise HTTPException(status_code=403, detail="This application is not for your circle.")

    if await _member_in_circle(db, circle.id, applicant.id):
        raise HTTPException(status_code=409, detail="Member is already in this circle.")

    if leader_status == LEADER_REJECTED:
        raise HTTPException(status_code=409, detail="Application was already rejected by the leader.")
    if leader_status == LEADER_APPROVED and decision == LEADER_APPROVED:
        raise HTTPException(status_code=409, detail="Application was already approved by the leader.")

    kyc = applicant.kyc_status.value if hasattr(applicant.kyc_status, "value") else str(applicant.kyc_status)

    if decision == LEADER_APPROVED:
        if kyc != KycStatus.approved.value:
            raise HTTPException(
                status_code=400,
                detail="Zenk must approve this member's KYC before you can add them to the circle.",
            )
        existing = await db.execute(
            select(CircleMember).where(
                CircleMember.circle_id == circle.id,
                CircleMember.user_id == applicant.id,
            )
        )
        if not existing.scalar_one_or_none():
            try:
                await assert_can_add_member(db, circle)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            db.add(
                CircleMember(
                    circle_id=circle.id,
                    user_id=applicant.id,
                    role="sponsor_member",
                )
            )

    applicant.admin_note = build_invite_note(circle.id, leader_status=decision)
    if decision == LEADER_APPROVED:
        from app.services.kia_event_briefings import emit_member_joined
        from app.services.student_circle_privacy import display_name_for_roster

        member_label, _, role_label = await display_name_for_roster(
            db, applicant, cm_role="sponsor_member"
        )
        await emit_member_joined(
            db,
            circle=circle,
            member_name=member_label,
            leader_name=user.full_name or "Circle leader",
            role_label=role_label,
        )
    await db.commit()

    try:
        await notify_user_leader_circle_decision(
            member_signup_id=applicant.id,
            member_name=applicant.full_name,
            circle_name=circle.name,
            approved=(decision == LEADER_APPROVED),
            db=db,
        )
    except Exception:
        pass

    return {
        "signup_id": applicant.id,
        "decision": decision,
        "circle_id": circle.id,
        "in_circle": decision == LEADER_APPROVED,
    }


@router.get("/check-circle-name")
async def check_circle_name(
    name: str,
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pre-submit check — circle display names are unique platform-wide."""
    from app.services.circle_name_validation import circle_name_taken, normalize_circle_name

    cleaned = normalize_circle_name(name)
    if len(cleaned) < 2:
        return {
            "available": False,
            "message": "Circle name must be at least 2 characters.",
        }
    taken = await circle_name_taken(db, cleaned, exclude_circle_id=circle_id)
    return {
        "available": not taken,
        "message": "This circle name is already in use. Choose a different name." if taken else None,
    }


@router.patch("/circle/{circle_id}/name")
async def patch_circle_name(
    circle_id: str,
    body: PatchCircleNameRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Direct rename is disabled — leaders must submit an admin-approved rename request."""
    circle, role = await resolve_user_circle(db, user.id, circle_id)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can rename the circle.")
    raise HTTPException(
        status_code=403,
        detail=(
            "Circle names cannot be changed directly. Submit a rename request from Circle Management "
            "(ZenK admin approval required; once every 90 days)."
        ),
    )


@router.get("/circle/{circle_id}/rename-status", response_model=CircleRenameStatusOut)
async def get_circle_rename_status(
    circle_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, role = await resolve_user_circle(db, user.id, circle_id)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can view rename status.")
    from app.services.circle_rename_ops import build_rename_status

    data = await build_rename_status(db, circle=circle)
    pending = data.get("pending_request")
    return CircleRenameStatusOut(
        can_request=data["can_request"],
        current_name=data["current_name"],
        next_eligible_at=data.get("next_eligible_at"),
        cooldown_days=data["cooldown_days"],
        pending_request=CircleAdminRequestOut(**pending) if pending else None,
        blocked_reason=data.get("blocked_reason"),
        policy_note=data["policy_note"],
    )


@router.post("/circle-rename-request", response_model=CircleAdminRequestCreateResponse)
async def submit_circle_rename_request(
    body: CircleRenameRequestBody,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.persona != Persona.sponsor_leader:
        raise HTTPException(status_code=403, detail="Only circle leaders can request a circle rename.")
    circle, role = await resolve_user_circle(db, user.id, body.circle_id)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can request a circle rename.")
    from app.services.circle_rename_ops import request_circle_rename

    try:
        req = await request_circle_rename(
            db,
            circle=circle,
            leader=user,
            new_name=body.new_name,
            comment=body.comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        from app.services.kia_event_briefings import emit_admin_circle_ops_submitted

        await emit_admin_circle_ops_submitted(db, req=req, circle_name=circle.name)
    except Exception:
        pass
    await db.commit()
    return CircleAdminRequestCreateResponse(
        message="Rename request sent to ZenK admin for review.",
        request=CircleAdminRequestOut(**request_to_dict(req, circle_name=circle.name)),
    )


@router.put("/budget", response_model=BudgetResponse)
async def update_budget(
    body: SetCircleBudgetRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Circle leader sets the annual budget for the current FY."""
    circle, role = await resolve_user_circle(db, user.id, body.circle_id)
    await set_circle_budget(
        db,
        user,
        body.annual_budget,
        fy_label=body.fy_label,
        circle_id=body.circle_id,
    )
    await db.refresh(circle)
    data = await _budget_payload_for_circle(db, circle, role)
    return BudgetResponse(**data)


def _initials(name: str) -> str:
    parts = (name or "").split()
    if not parts:
        return "?"
    return "".join(p[0] for p in parts[:2]).upper()


@router.get("/participation", response_model=ParticipationResponse)
async def get_participation(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-member impact activity for the circle (visible to all members)."""
    circle, role = await resolve_user_circle(db, user.id, circle_id)
    data = await build_member_participation(
        db, circle, current_user_id=user.id, viewer_role=role
    )
    sponsored = data.get("sponsored_student")
    return ParticipationResponse(
        members=[Member(**m) for m in data["members"]],
        sponsored_student=SponsoredStudentSummary(**sponsored) if sponsored else None,
        circle_avg_pct=data.get("circle_avg_pct"),
        leader_name=data.get("leader_name") or "",
        leader_pct=data.get("leader_pct"),
        circle_total_hrs=data.get("circle_total_hrs"),
        period_label=data.get("period_label") or "This month",
        metrics_available=data.get("metrics_available", True),
        message=data.get("message"),
        member_count=data.get("member_count", 0),
        member_limit=data.get("member_limit", 5),
        is_leader=data.get("is_leader", False),
        can_request_limit_increase=data.get("can_request_limit_increase", False),
        pending_admin_requests=data.get("pending_admin_requests", 0),
    )


@router.post("/member-removal-request", response_model=CircleAdminRequestCreateResponse)
async def submit_member_removal_request(
    body: MemberRemovalRequestBody,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.persona != Persona.sponsor_leader:
        raise HTTPException(status_code=403, detail="Only circle leaders can request member removal.")
    circle, role = await resolve_user_circle(db, user.id, body.circle_id)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can request member removal.")
    try:
        req = await request_member_removal(
            db,
            circle=circle,
            leader=user,
            target_user_id=body.target_user_id,
            comment=body.comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        from app.services.kia_event_briefings import emit_admin_circle_ops_submitted

        await emit_admin_circle_ops_submitted(db, req=req, circle_name=circle.name)
    except Exception:
        pass
    await db.commit()
    return CircleAdminRequestCreateResponse(
        message="Removal request sent to ZenK admin for review.",
        request=CircleAdminRequestOut(**request_to_dict(req, circle_name=circle.name)),
    )


@router.post("/member-limit-request", response_model=CircleAdminRequestCreateResponse)
async def submit_member_limit_request(
    body: MemberLimitRequestBody,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.persona != Persona.sponsor_leader:
        raise HTTPException(status_code=403, detail="Only circle leaders can request a higher member cap.")
    circle, role = await resolve_user_circle(db, user.id, body.circle_id)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can request a higher member cap.")
    try:
        req = await request_member_limit_increase(
            db,
            circle=circle,
            leader=user,
            requested_limit=body.requested_limit,
            comment=body.comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        from app.services.kia_event_briefings import emit_admin_circle_ops_submitted

        await emit_admin_circle_ops_submitted(db, req=req, circle_name=circle.name)
    except Exception:
        pass
    await db.commit()
    return CircleAdminRequestCreateResponse(
        message="Member limit increase sent to ZenK admin for approval.",
        request=CircleAdminRequestOut(**request_to_dict(req, circle_name=circle.name)),
    )


@router.get("/admin-requests", response_model=list[CircleAdminRequestOut])
async def list_circle_admin_requests_route(
    circle_id: Optional[str] = None,
    status: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, role = await resolve_user_circle(db, user.id, circle_id)
    if not _can_set_budget(role) and user.persona != Persona.sponsor_leader:
        raise HTTPException(status_code=403, detail="Leader access required.")
    rows = await list_circle_admin_requests(db, circle.id, status=status)
    return [CircleAdminRequestOut(**r) for r in rows]


def _latest_subject_score(
    rows: list, labels: tuple[str, ...]
) -> tuple[Optional[int], Optional[int]]:
    """Return (score, baseline) from latest matching subject row if any."""
    for row in sorted(rows, key=lambda r: (r.quarter or ""), reverse=True):
        subj = (row.subject or "").strip().lower()
        if subj in labels or any(l in subj for l in labels):
            score = int(round(float(row.score or 0)))
            return score, max(0, score - 5)
    return None, None


@router.get("/student-update", response_model=StudentUpdateResponse)
async def get_student_update(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.school import SchoolStudent, SchoolStudentSubjectScore

    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    res = await db.execute(
        select(SchoolStudent)
        .where(SchoolStudent.circle_id == circle.id)
        .order_by(SchoolStudent.created_at.desc())
        .limit(1)
    )
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=404,
            detail="No sponsored students in your circle yet. Approve school enrollments to see updates.",
        )

    subj_res = await db.execute(
        select(SchoolStudentSubjectScore).where(
            SchoolStudentSubjectScore.student_id == student.id
        )
    )
    subject_rows = list(subj_res.scalars().all())

    maths, maths_base = _latest_subject_score(
        subject_rows, ("maths", "mathematics", "math")
    )
    science, science_base = _latest_subject_score(
        subject_rows, ("science", "physics", "chemistry", "biology")
    )

    avg = int(student.avg_score or 0)
    zqa = int(student.zqa_score or avg)
    baseline = max(0, zqa - int(student.zqa_baseline_delta or 0))

    from app.services.student_circle_privacy import mask_student_for_circle

    masked = await mask_student_for_circle(db, student)

    return StudentUpdateResponse(
        student_name=masked["pseudonym"],
        sl_name=masked.get("sl_name"),
        maths_score=maths if maths is not None else avg,
        maths_baseline=maths_base if maths_base is not None else baseline,
        science_score=science if science is not None else avg,
        science_baseline=science_base if science_base is not None else baseline,
        attendance_pct=int(student.attendance_pct or 0),
        improvement_pts=max(0, int(student.zqa_baseline_delta or 0)),
        school_comment=(
            student.tutor_recommendation
            or "Latest ZQA and attendance are shown from your school's records."
        ),
    )


@router.get("/sponsored-student", response_model=SponsoredStudentProfileResponse)
async def get_sponsored_student_profile(
    circle_id: Optional[str] = None,
    quarter: str = "Q4",
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full masked academics for the circle's sponsored student (leaders + members)."""
    from app.services.sponsor_sponsored_student import sponsored_student_profile_for_circle

    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    profile = await sponsored_student_profile_for_circle(db, circle.id, quarter=quarter)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="No sponsored student linked to your circle yet. Approve a school enrollment or accept a student interest request.",
        )
    return SponsoredStudentProfileResponse(**profile)


@router.get("/time-impact", response_model=TimeImpactResponse)
async def get_time_impact(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    data = await build_time_impact(db, circle.id)
    return TimeImpactResponse(**data)


@router.get("/rankings", response_model=RankingsResponse)
async def get_rankings(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Platform-wide rankings are not published yet; return your circle only when ZQA exists."""
    from app.models.school import SchoolStudent

    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    avg_res = await db.execute(
        select(func.avg(SchoolStudent.zqa_score)).where(SchoolStudent.circle_id == circle.id)
    )
    avg = avg_res.scalar_one()
    if avg is None:
        return RankingsResponse(
            circles=[],
            platform_rankings_available=False,
            message="No ZQA data yet. Rankings appear after students are enrolled and schools submit reports.",
        )
    zenq = int(round(float(avg)))
    return RankingsResponse(
        circles=[
            CircleRankRow(
                rank=1,
                name=circle.name,
                zenq=zenq,
                city="",
                is_mine=True,
            )
        ],
        platform_rankings_available=False,
        message="Showing your circle only. National circle rankings are not published yet.",
    )


@router.get("/budget-insight", response_model=KiaInsightResponse)
async def get_budget_insight(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    budget_data = {
        "total_budget": 0,
        "spent": 0,
        "collected": 0,
        "balance_to_spend": 0,
        "fy_label": "FY 2025-26",
    }
    try:
        circle, role = await resolve_user_circle(db, user.id, circle_id)
        budget_data = await _budget_payload_for_circle(db, circle, role)
    except HTTPException:
        pass

    insight = await generate_budget_insight(budget_data)
    
    return KiaInsightResponse(
        analysis=insight.get("analysis", ""),
        suggestion=insight.get("suggestion", ""),
        coordinator_name=insight.get("coordinator_name", "Rohit")
    )


@router.post("/provision-circle")
async def provision_circle(
    body: ProvisionCircleRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approved sponsor leader creates their circle (idempotent if one already exists)."""
    if user.persona != Persona.sponsor_leader:
        raise HTTPException(status_code=403, detail="Only sponsor leaders can create a circle.")
    try:
        result = await provision_leader_circle(db, user, name=body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


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
    Disabled unless ZENK_ALLOW_DEMO_CIRCLE=true / settings.allow_demo_circle.
    """
    if not settings.allow_demo_circle:
        raise HTTPException(
            status_code=403,
            detail="Demo circle join is disabled. Use your real circle membership.",
        )
    persona = str(user.persona or "").lower()
    if persona not in ("sponsor", "sponsor_leader", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Demo circle join is not available for circle members.",
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


@router.get("/student-interests")
async def list_circle_student_interests(
    circle_id: str,
    status: str = "pending_leader",
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v2: anonymous student circle interest requests for leaders (grade/attendance brief, no legal name)."""
    from app.services.student_onboarding_v2 import list_leader_circle_interests

    return await list_leader_circle_interests(db, user, circle_id, status=status)


@router.post("/student-interests/{request_id}/accept")
async def accept_circle_student_interest(
    request_id: str,
    body: dict,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.student_onboarding_v2 import leader_decide_circle_interest

    return await leader_decide_circle_interest(
        db,
        request_id=request_id,
        leader=user,
        action="accept",
        note=(body.get("note") or "").strip() or None,
    )


@router.post("/student-interests/{request_id}/reject")
async def reject_circle_student_interest(
    request_id: str,
    body: dict,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.student_onboarding_v2 import leader_decide_circle_interest

    return await leader_decide_circle_interest(
        db,
        request_id=request_id,
        leader=user,
        action="reject",
        note=(body.get("note") or "").strip() or None,
    )


@router.get("/student-interests/{request_id}/probe-messages")
async def leader_probe_messages(
    request_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.student_onboarding_v2 import list_probe_messages

    return await list_probe_messages(db, request_id, user)


@router.post("/student-interests/{request_id}/probe-messages")
async def leader_post_probe(
    request_id: str,
    body: dict,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.student_onboarding_v2 import post_probe_message

    return await post_probe_message(
        db,
        request_id=request_id,
        sender=user,
        body=(body.get("body") or "").strip(),
        sender_role="leader",
    )


@router.get("/statement", response_model=StatementResponse)
async def get_statement(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    return StatementResponse(**await build_statement(db, circle))


@router.get("/vendor-payments", response_model=list[VendorPaymentRow])
async def get_vendor_payments(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    return [VendorPaymentRow(**r) for r in await build_vendor_payments(db, circle)]


@router.get("/vendor-payments/dashboard", response_model=VendorPaymentsDashboardResponse)
async def get_vendor_payments_dashboard(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.circle_vendor_disbursements import build_vendor_payments_dashboard

    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    data = await build_vendor_payments_dashboard(db, circle)
    return VendorPaymentsDashboardResponse(
        total_disbursed=data["total_disbursed"],
        total_pending=data["total_pending"],
        vendors_served=data["vendors_served"],
        payment_history=[DisbursementHistoryRow(**r) for r in data["payment_history"]],
        payees=[CirclePayeeResponse(**p) for p in data["payees"]],
        next_deposit_request=(
            DepositRequestAlert(**data["next_deposit_request"])
            if data.get("next_deposit_request")
            else None
        ),
        gateway_provider=data.get("gateway_provider", "ICICI Bank"),
    )


@router.get("/payees", response_model=list[CirclePayeeResponse])
async def list_payees(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.circle_vendor_disbursements import list_circle_payees

    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    return [CirclePayeeResponse(**p) for p in await list_circle_payees(db, circle.id)]


@router.post("/payees", response_model=CirclePayeeResponse, status_code=201)
async def create_payee(
    body: CirclePayeeCreateRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.circle_vendor_disbursements import create_circle_payee

    circle, role = await resolve_user_circle(db, user.id, body.circle_id or None)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can add payees.")
    try:
        row = await create_circle_payee(
            db,
            circle_id=circle.id,
            created_by=user.id,
            display_name=body.display_name,
            beneficiary_name=body.beneficiary_name,
            category=body.category,
            account_number=body.account_number,
            ifsc=body.ifsc,
            bank_name=body.bank_name,
            upi_id=body.upi_id,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return CirclePayeeResponse(**row)


@router.post("/disbursements/initiate", response_model=InitiateDisbursementResponse)
async def initiate_payee_disbursement(
    body: InitiateDisbursementRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as date_type

    from app.services.circle_vendor_disbursements import initiate_disbursement

    circle, role = await resolve_user_circle(db, user.id, body.circle_id or None)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can initiate payments.")
    due: Optional[date_type] = None
    if body.due_date:
        try:
            due = date_type.fromisoformat(body.due_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid due_date (use YYYY-MM-DD)") from exc
    try:
        result = await initiate_disbursement(
            db,
            circle=circle,
            user=user,
            payee_id=body.payee_id,
            amount_inr=body.amount_inr,
            description=body.description or "",
            due_date=due,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return InitiateDisbursementResponse(**result)


@router.post(
    "/disbursements/{disbursement_id}/complete",
    response_model=DisbursementHistoryRow,
)
async def complete_payee_disbursement(
    disbursement_id: str,
    body: CompleteDisbursementRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.circle_vendor_disbursements import complete_disbursement

    circle, _ = await resolve_user_circle(db, user.id, body.circle_id or None)
    try:
        row = await complete_disbursement(
            db,
            circle_id=circle.id,
            disbursement_id=disbursement_id,
            session_id=body.session_id,
            success=body.success,
            gateway_ref=body.gateway_ref,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return DisbursementHistoryRow(**row)


@router.get("/member-contributions", response_model=MemberContributionsResponse)
async def get_member_contributions(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    data = await build_member_contributions(db, circle)
    return MemberContributionsResponse(
        tracking_available=data["tracking_available"],
        members=[MemberContributionRow(**m) for m in data["members"]],
        total_collected=data["total_collected"],
        total_budget=data["total_budget"],
        funded_pct=data["funded_pct"],
        spent=data["spent"],
        message=data["message"],
    )


@router.get("/profile-pulse", response_model=ProfilePulseResponse)
async def get_profile_pulse(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    data = await build_profile_pulse(db, circle, user)
    return ProfilePulseResponse(
        circle_feed=[PulseItem(**i) for i in data["circle_feed"]],
        global_feed=[PulseItem(**i) for i in data["global_feed"]],
        global_available=data["global_available"],
        global_news_status=data.get("global_news_status"),
        global_news_message=data.get("global_news_message"),
        global_news_stale=data.get("global_news_stale", False),
        badges=[SponsorBadge(**b) for b in data["badges"]],
        badges_available=data["badges_available"],
        badges_earned_count=data.get("badges_earned_count", 0),
        badges_total=data.get("badges_total", 0),
        streaks=[SponsorStreak(**s) for s in data.get("streaks", [])],
    )


@router.get("/impact-league", response_model=ImpactLeagueResponse)
async def get_impact_league(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.school import SchoolStudent

    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    student_res = await db.execute(
        select(func.count()).select_from(SchoolStudent).where(SchoolStudent.circle_id == circle.id)
    )
    count = int(student_res.scalar_one() or 0)
    avg_res = await db.execute(
        select(func.avg(SchoolStudent.zqa_score)).where(SchoolStudent.circle_id == circle.id)
    )
    avg = avg_res.scalar_one()
    if count == 0 or avg is None:
        return ImpactLeagueResponse(
            rows=[],
            available=False,
            message="Impact League needs sponsored students with ZQA data. Enroll students via School Comm first.",
        )
    return ImpactLeagueResponse(
        rows=[
            ImpactLeagueRow(
                rank=1,
                circle_name=circle.name,
                impact_score=int(round(float(avg))),
                student_count=count,
                zenq_avg=int(round(float(avg))),
            )
        ],
        available=True,
        message="Showing your circle only. Cross-circle league tables are not published yet.",
    )


@router.get("/impact-improvement", response_model=ImpactImprovementResponse)
async def get_impact_improvement(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    data = await build_impact_improvement(db, circle.id)
    return ImpactImprovementResponse(**data)


@router.get("/students", response_model=list[CircleStudentRow])
async def list_circle_students(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    rows = await build_circle_students(db, circle.id)
    return [CircleStudentRow(**r) for r in rows]


@router.get("/school-partner", response_model=SchoolPartnerResponse)
async def get_school_partner(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partner school linked via enrolled students (for School Comm tab)."""
    from app.services.circle_school_partner import resolve_school_partner_for_circle

    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    partner = await resolve_school_partner_for_circle(db, circle.id)
    if not partner:
        raise HTTPException(
            status_code=404,
            detail="No partner school linked yet. Approve a student interest request or school enrollment first.",
        )
    return SchoolPartnerResponse(**partner)


@router.get("/school-partner/messages", response_model=list[SchoolPartnerMessage])
async def list_school_partner_messages(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.circle_school_partner import (
        fetch_partner_messages,
        resolve_school_partner_for_circle,
    )

    circle, _ = await resolve_user_circle(db, user.id, circle_id)
    partner = await resolve_school_partner_for_circle(db, circle.id)
    if not partner:
        raise HTTPException(status_code=404, detail="No partner school linked to this circle.")
    rows = await fetch_partner_messages(
        db, circle_id=circle.id, school_id=partner["school_id"]
    )
    return [SchoolPartnerMessage(**r) for r in rows]


@router.post("/school-partner/messages", response_model=SchoolPartnerMessage)
async def post_school_partner_message(
    body: SchoolPartnerMessageRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.circle_school_partner import (
        post_partner_message,
        resolve_school_partner_for_circle,
    )

    circle, role = await resolve_user_circle(db, user.id, body.circle_id or None)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can message partner schools.")
    partner = await resolve_school_partner_for_circle(db, circle.id)
    if not partner:
        raise HTTPException(status_code=404, detail="No partner school linked to this circle.")
    try:
        row = await post_partner_message(
            db,
            circle_id=circle.id,
            school_id=partner["school_id"],
            sender_side="circle",
            body=body.body,
            sender_signup=user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return SchoolPartnerMessage(**row)


@router.post("/invite-link", response_model=CircleInviteLinkResponse)
async def create_invite_link(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.persona != Persona.sponsor_leader:
        raise HTTPException(status_code=403, detail="Only circle leaders can create invite links.")
    circle, role = await resolve_user_circle(db, user.id, circle_id)
    if not _can_set_budget(role):
        raise HTTPException(status_code=403, detail="Only circle leaders can create invite links.")
    row = await create_circle_invite_token(db, circle_id=circle.id, created_by=user.id)
    base = (settings.frontend_base_url or settings.website_url or "http://localhost:5173").rstrip(
        "/"
    )
    invite_url = f"{base}/join/circle?invite={row.token}"
    return CircleInviteLinkResponse(
        token=row.token,
        invite_url=invite_url,
        expires_at=row.expires_at,
        circle_id=circle.id,
        circle_name=circle.name,
    )


@router.get("/invite/resolve", response_model=InviteResolveResponse)
async def resolve_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    resolved = await resolve_invite_token(db, token)
    if not resolved:
        raise HTTPException(status_code=404, detail="Invite link is invalid or expired.")
    cid, cname = resolved
    return InviteResolveResponse(circle_id=cid, circle_name=cname)


@router.post("/student-cart/submit", response_model=StudentCartSubmissionOut)
async def submit_circle_student_cart(
    body: StudentCartSubmitRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, _ = await resolve_user_circle(db, user.id, body.circle_id)
    items = [it.model_dump() for it in body.items]
    data = await submit_student_cart(
        db,
        user,
        circle_id=circle.id,
        items=items,
        delivery_address=body.delivery_address,
        phone_number=body.phone_number,
    )
    return StudentCartSubmissionOut(**data)


@router.get("/student-cart/pending", response_model=list[StudentCartSubmissionOut])
async def list_pending_student_carts(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_pending_carts(db, user, circle_id)
    return [StudentCartSubmissionOut(**r) for r in rows]


@router.post("/student-cart/{submission_id}/decision", response_model=StudentCartSubmissionOut)
async def decide_circle_student_cart(
    submission_id: str,
    body: StudentCartDecisionRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    decision = (body.decision or "").strip().lower()
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be approved or rejected.")
    data = await decide_student_cart(
        db,
        user,
        submission_id,
        decision=decision,
        circle_id=body.circle_id,
    )
    return StudentCartSubmissionOut(**data)
