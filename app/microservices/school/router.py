from __future__ import annotations
from contextvars import ContextVar
from datetime import datetime
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.core.jwt_auth import get_current_user
from app.core.datetime_utils import to_utc_iso
from app.models.signup import SignupRequest
from app.models.enums import Persona, KycStatus
from app.models.school import (
    SchoolProfile, SchoolStudent, SchoolReport,
    SchoolAttendance, SchoolKiaMessage, SchoolKiaWelcome,
    SchoolStudentSubjectScore, SchoolStudentBloomsAssessment,
    SchoolStudentSEL, SchoolStudentNarrative, SchoolFormSubmission,
    SchoolStudentEnrollmentRequest, SchoolActionAuditLog, SchoolPortalMember,
)
from app.services.school_permissions import (
    has_permission,
    permissions_for_role,
    normalize_role,
    ROLE_PRINCIPAL,
    ROLE_STAFF,
)
from app.services.school_context import SchoolContext, resolve_school_context
from app.microservices.school.schemas import (
    SchoolProfileResponse, SchoolPhotoUploadResponse, SchoolStudentResponse, SchoolReportResponse,
    SchoolAttendanceResponse, SchoolZQAStudentResponse,
    SchoolKiaPrioritiesResponse, SchoolKiaPriorityItem,
    SchoolKiaChatRequest, SchoolKiaChatResponse,
    SchoolKiaMessageResponse, SchoolKiaWelcomeResponse,
    TutorRecommendationAction, SchoolStudentDetailResponse,
    SchoolStudentSubjectScoreResponse, SchoolStudentBloomsAssessmentResponse,
    SchoolStudentSELResponse, SchoolStudentNarrativeResponse,
    QuarterlyReportSubmitRequest, QuarterlyReportSubmitResponse,
    SchoolFormSubmissionResponse, SchoolCsvImportResponse,
    SchoolPdfExtractResponse, SchoolPendingReviewResponse, SchoolReviewApproveRequest,
    SchoolAttendanceImportResponse,
    SchoolAttendanceEntryRequest,
    SchoolAttendanceEntryResponse,
    SchoolCircleOption,
    SchoolFacultyResponse,
    SchoolFacultyCreateRequest,
    SchoolFacultyUpdateRequest,
    SchoolStudentFacultyAssignRequest,
    SchoolStudentEnrollRequest,
    SchoolEnrollmentRequestResponse,
    SchoolEnrollmentCreateResponse,
    PendingStudentSignupResponse,
    AdmitStudentSignupRequest,
    AdmitStudentSignupResponse,
    SchoolAuditLogEntry,
    SchoolPortalMemberResponse,
    SchoolPortalMemberCreateRequest,
    SchoolPortalMemberUpdateRequest,
    SchoolPortalInviteResponse,
    SchoolProfileCompletionResponse,
    SchoolProfileUpdateRequest,
    SchoolPartnerCircleResponse,
    SchoolPartnerMessageResponse,
    SchoolPartnerMessageRequest,
)
from app.services.school_portal_invite import create_portal_invite, build_join_url
from app.services.school_profile_completion import (
    is_profile_complete,
    profile_completion_payload,
    update_school_profile_fields,
)
from app.services.school_constants import VALID_AFFILIATION_IDS
from app.services.school_invite_email import send_school_portal_invite_email
from app.models.school import SchoolPortalInvite
from app.services.school_reports import apply_quarterly_report, latest_submission_map, _recalc_school_profile
from app.services.school_zqa_engine import get_zqa_breakdown, recompute_and_apply_zqa
from app.services.school_csv_import import csv_template_text, import_quarterly_csv
from app.services.school_report_templates import import_guide_text, generate_blank_report_pdf
from app.services.school_pdf_extract import process_pdf_upload, approve_pdf_review
from app.services.school_report_validate import validate_quarterly_payload
from app.services.school_attendance_import import (
    attendance_csv_template,
    import_attendance_csv,
    save_attendance_entry,
)
from app.services.kia_school import (
    fetch_school_context,
    generate_school_response,
    generate_school_priorities,
)
from app.services.school_student_enrollment import (
    list_active_circles,
    create_enrollment_request,
    enrollment_request_to_dict,
)
from app.services.school_student_admit import (
    admit_student_signup,
    list_pending_student_signups,
)
from app.services.student_onboarding_v2 import (
    approve_school_interest,
    list_principal_school_interests,
    reject_school_interest,
)
from app.services.cloudinary_service import upload_image
from app.microservices.parent.schemas import (
    SchoolParentSubmissionOut,
    ParentReviewRequest,
    ParentRejectRequest,
)
from app.services.parent_portal import (
    list_school_parent_submissions,
    approve_parent_submission,
    reject_parent_submission,
)

logger = logging.getLogger(__name__)

_school_ctx_var: ContextVar[Optional[SchoolContext]] = ContextVar("school_ctx", default=None)


async def _bind_school_context(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    _require_school(user)
    _school_ctx_var.set(await resolve_school_context(user, db))


def _school_ctx() -> SchoolContext:
    ctx = _school_ctx_var.get()
    if ctx is None:
        raise RuntimeError("School context not initialized")
    return ctx


def _school_id() -> str:
    return _school_ctx().school_id


router = APIRouter(
    prefix="/school",
    tags=["School Dashboard"],
    dependencies=[Depends(_bind_school_context)],
)

_SUBJECT_TO_KEY = {
    "Maths": "maths",
    "Science": "science",
    "English": "english",
    "Social": "social",
    "Hindi": "hindi",
    "Sanskrit": "sanskrit",
}

_QUARTER_META = {
    "Q4": ("Q4 2025-26", "JAN-MAR 2026"),
    "Q3": ("Q3 2025-26", "OCT-DEC 2025"),
    "Q2": ("Q2 2025-26", "JUL-SEP 2025"),
    "Q1": ("Q1 2025-26", "APR-JUN 2025"),
}

_QUARTER_ORDER = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}


def _require_school(user: SignupRequest) -> SignupRequest:
    if user.persona != Persona.school:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="School dashboard is restricted to school accounts.",
        )
    return user


def _require_school_verified(user: SignupRequest) -> SignupRequest:
    _require_school(user)
    if user.kyc_status != KycStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an approved school account.",
        )
    return user


async def _audit_school_action(
    db: AsyncSession,
    user: SignupRequest,
    school_id: str,
    action: str,
    *,
    student_id: Optional[str] = None,
    outcome: str = "success",
    detail: Optional[dict] = None,
) -> None:
    logger.info(
        "school_action user_id=%s email=%s action=%s student_id=%s outcome=%s",
        user.id,
        user.email,
        action,
        student_id or "-",
        outcome,
    )
    db.add(
        SchoolActionAuditLog(
            school_id=school_id,
            actor_user_id=user.id,
            actor_email=user.email,
            action=action,
            student_id=student_id,
            outcome=outcome,
            detail=detail,
        )
    )


async def _enforce_school_permission(
    db: AsyncSession,
    user: SignupRequest,
    permission: str,
    *,
    audit_action: Optional[str] = None,
    student_id: Optional[str] = None,
) -> SchoolProfile:
    """KYC-approved school user with the given portal permission."""
    _require_school_verified(user)
    ctx = _school_ctx()
    role = ctx.portal_role
    if not has_permission(role, permission):
        if audit_action:
            await _audit_school_action(
                db,
                user,
                ctx.school_id,
                audit_action,
                student_id=student_id,
                outcome="denied",
                detail={"required_permission": permission, "portal_role": role},
            )
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires permission '{permission}'. Your role is '{role}'.",
        )
    return ctx.profile


def _profile_to_response(ctx: SchoolContext) -> SchoolProfileResponse:
    profile = ctx.profile
    role = ctx.portal_role
    return SchoolProfileResponse(
        id=profile.id,
        school_name=profile.school_name,
        school_code=profile.school_code,
        affiliation=profile.affiliation,
        city=profile.city,
        district=profile.district,
        principal_name=profile.principal_name,
        partner_since=profile.partner_since,
        is_partner=profile.is_partner,
        fy_current=profile.fy_current,
        total_enrolled=profile.total_enrolled,
        avg_attendance=profile.avg_attendance,
        avg_academic_score=profile.avg_academic_score,
        next_zqa_date=profile.next_zqa_date,
        reports_pending=profile.reports_pending,
        school_logo_url=profile.school_logo_url,
        principal_photo_url=profile.principal_photo_url,
        portal_role=role,
        permissions=permissions_for_role(role),
        is_account_owner=ctx.is_account_owner,
        actor_name=ctx.actor_name,
        login_email=ctx.actor_email,
        can_manage_portal_access=ctx.can_manage_portal_access,
        affiliation_number=profile.affiliation_number,
        enrollment_year=profile.enrollment_year,
        profile_completed_at=(
            profile.profile_completed_at.isoformat() if profile.profile_completed_at else None
        ),
        profile_complete=is_profile_complete(profile),
        onboarding_source=profile.onboarding_source,
    )


async def _require_profile_complete(ctx: SchoolContext) -> None:
    if not is_profile_complete(ctx.profile):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete your school profile (affiliation number and ZenK enrollment year) before admitting students.",
        )


_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
_ALLOWED_CSV_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel"}
_ALLOWED_PDF_TYPES = {"application/pdf"}
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_CSV_BYTES = 2 * 1024 * 1024
_MAX_PDF_BYTES = 10 * 1024 * 1024


async def _upload_profile_image(file: UploadFile, folder: str) -> str:
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a JPG, PNG, or WebP image.",
        )
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    if len(payload) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image must be <= 5 MB.")
    await file.seek(0)
    url = await upload_image(file, folder=folder)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image upload is unavailable. Check Cloudinary configuration.",
        )
    return url


@router.get("/profile", response_model=SchoolProfileResponse)
async def get_profile(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    return _profile_to_response(_school_ctx())


@router.get("/profile/completion", response_model=SchoolProfileCompletionResponse)
async def get_profile_completion(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    ctx = _school_ctx()
    return SchoolProfileCompletionResponse(**profile_completion_payload(ctx.profile))


@router.patch("/profile", response_model=SchoolProfileResponse)
async def patch_profile(
    body: SchoolProfileUpdateRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db, user, "manage_school_identity", audit_action="update_school_profile"
    )
    ctx = _school_ctx()
    if body.affiliation and body.affiliation.strip().upper() not in VALID_AFFILIATION_IDS:
        raise HTTPException(status_code=400, detail="Invalid affiliation.")
    if body.enrollment_year and body.enrollment_year.strip():
        year = body.enrollment_year.strip()
        if not (year.isdigit() and 1950 <= int(year) <= 2100):
            raise HTTPException(status_code=400, detail="Enrollment year must be a valid year.")
    await update_school_profile_fields(
        db,
        profile,
        school_name=body.school_name,
        principal_name=body.principal_name,
        affiliation=body.affiliation,
        affiliation_number=body.affiliation_number,
        enrollment_year=body.enrollment_year,
        city=body.city,
        district=body.district,
    )
    await db.commit()
    return _profile_to_response(ctx)


@router.get("/audit-log", response_model=List[SchoolAuditLogEntry])
async def get_audit_log(
    limit: int = 50,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db, user, "view_audit_log", audit_action="view_audit_log"
    )
    cap = max(1, min(limit, 200))
    res = await db.execute(
        select(SchoolActionAuditLog)
        .where(SchoolActionAuditLog.school_id == profile.id)
        .order_by(SchoolActionAuditLog.created_at.desc())
        .limit(cap)
    )
    rows = res.scalars().all()
    return [
        SchoolAuditLogEntry(
            id=r.id,
            action=r.action,
            student_id=r.student_id,
            outcome=r.outcome,
            actor_email=r.actor_email,
            detail=r.detail,
            created_at=to_utc_iso(r.created_at),
        )
        for r in rows
    ]


def _portal_member_response(member: SchoolPortalMember) -> SchoolPortalMemberResponse:
    return SchoolPortalMemberResponse(
        id=member.id,
        email=member.email,
        display_name=member.display_name,
        portal_role=normalize_role(member.portal_role),
        user_id=member.user_id,
        is_linked=bool(member.user_id),
        created_at=member.created_at.isoformat(),
    )


@router.get("/portal-members", response_model=List[SchoolPortalMemberResponse])
async def list_portal_members(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "manage_portal_access")
    ctx = _school_ctx()
    res = await db.execute(
        select(SchoolPortalMember)
        .where(SchoolPortalMember.school_id == ctx.school_id)
        .order_by(SchoolPortalMember.created_at.desc())
    )
    return [_portal_member_response(m) for m in res.scalars().all()]


def _invite_status(invite: SchoolPortalInvite) -> str:
    now = datetime.utcnow()
    if invite.revoked_at is not None:
        return "revoked"
    if invite.accepted_at is not None:
        return "accepted"
    if invite.expires_at < now:
        return "expired"
    return "pending"


def _invite_response(invite: SchoolPortalInvite, *, email_sent: bool = False) -> SchoolPortalInviteResponse:
    return SchoolPortalInviteResponse(
        id=invite.id,
        email=invite.email,
        display_name=invite.display_name,
        portal_role=normalize_role(invite.portal_role),
        join_url=build_join_url(invite.token),
        expires_at=invite.expires_at.isoformat(),
        status=_invite_status(invite),
        member_id=invite.member_id,
        created_at=invite.created_at.isoformat(),
        email_sent=email_sent,
    )


@router.get("/invites", response_model=List[SchoolPortalInviteResponse])
async def list_portal_invites(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "manage_portal_access")
    ctx = _school_ctx()
    res = await db.execute(
        select(SchoolPortalInvite)
        .where(SchoolPortalInvite.school_id == ctx.school_id)
        .order_by(SchoolPortalInvite.created_at.desc())
        .limit(100)
    )
    return [_invite_response(i) for i in res.scalars().all()]


@router.post("/invites", response_model=SchoolPortalInviteResponse)
async def create_invite(
    body: SchoolPortalMemberCreateRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create invite link for staff/faculty (preferred over email-only onboarding)."""
    await _enforce_school_permission(db, user, "manage_portal_access")
    ctx = _school_ctx()
    try:
        invite, _url = await create_portal_invite(
            db,
            school_id=ctx.school_id,
            email=body.email,
            display_name=body.display_name,
            portal_role=body.portal_role,
            invited_by_user_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await _audit_school_action(
        db,
        user,
        ctx.school_id,
        "create_portal_invite",
        outcome="success",
        detail={"email": invite.email, "portal_role": invite.portal_role},
    )
    await db.commit()
    await db.refresh(invite)

    join_url = build_join_url(invite.token)
    email_sent = await send_school_portal_invite_email(
        to_email=invite.email,
        display_name=invite.display_name,
        school_name=ctx.profile.school_name,
        portal_role=invite.portal_role,
        join_url=join_url,
        expires_at_iso=invite.expires_at.strftime("%d %b %Y %H:%M UTC"),
    )
    return _invite_response(invite, email_sent=email_sent)


@router.delete("/invites/{invite_id}")
async def revoke_invite(
    invite_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "manage_portal_access")
    ctx = _school_ctx()
    res = await db.execute(
        select(SchoolPortalInvite).where(
            SchoolPortalInvite.id == invite_id,
            SchoolPortalInvite.school_id == ctx.school_id,
        )
    )
    invite = res.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found.")
    invite.revoked_at = datetime.utcnow()
    await _audit_school_action(
        db,
        user,
        ctx.school_id,
        "revoke_portal_invite",
        outcome="success",
        detail={"email": invite.email},
    )
    await db.commit()
    return {"status": "success", "message": f"Invite for {invite.email} revoked."}


@router.post("/portal-members", response_model=SchoolPortalInviteResponse)
async def add_portal_member(
    body: SchoolPortalMemberCreateRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias for POST /school/invites — returns invite link."""
    return await create_invite(body, user, db)


@router.patch("/portal-members/{member_id}", response_model=SchoolPortalMemberResponse)
async def update_portal_member(
    member_id: str,
    body: SchoolPortalMemberUpdateRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "manage_portal_access")
    ctx = _school_ctx()
    res = await db.execute(
        select(SchoolPortalMember).where(
            SchoolPortalMember.id == member_id,
            SchoolPortalMember.school_id == ctx.school_id,
        )
    )
    member = res.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Portal member not found.")
    if body.display_name is not None:
        member.display_name = body.display_name.strip()
    if body.portal_role is not None:
        member.portal_role = normalize_role(body.portal_role)
    await _audit_school_action(
        db,
        user,
        ctx.school_id,
        "update_portal_member",
        outcome="success",
        detail={"member_id": member_id, "portal_role": member.portal_role},
    )
    await db.commit()
    await db.refresh(member)
    return _portal_member_response(member)


@router.delete("/portal-members/{member_id}")
async def remove_portal_member(
    member_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "manage_portal_access")
    ctx = _school_ctx()
    res = await db.execute(
        select(SchoolPortalMember).where(
            SchoolPortalMember.id == member_id,
            SchoolPortalMember.school_id == ctx.school_id,
        )
    )
    member = res.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Portal member not found.")
    await db.delete(member)
    await _audit_school_action(
        db,
        user,
        ctx.school_id,
        "remove_portal_member",
        outcome="success",
        detail={"email": member.email},
    )
    await db.commit()
    return {"status": "success", "message": f"Removed portal access for {member.email}."}


@router.get("/faculty", response_model=List[SchoolFacultyResponse])
async def list_school_faculty(
    role: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "view_faculty_registry")
    from app.services.school_faculty_registry import list_faculty

    ctx = _school_ctx()
    return [SchoolFacultyResponse(**row) for row in await list_faculty(db, ctx.school_id, role=role)]


@router.post("/faculty", response_model=SchoolFacultyResponse)
async def create_school_faculty(
    body: SchoolFacultyCreateRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "manage_faculty_registry")
    from app.services.school_faculty_registry import create_faculty

    ctx = _school_ctx()
    row = await create_faculty(
        db,
        ctx.school_id,
        display_name=body.display_name,
        faculty_role=body.faculty_role,
        subject=body.subject,
        email=body.email,
        portal_member_id=body.portal_member_id,
        notes=body.notes,
    )
    await _audit_school_action(
        db,
        user,
        ctx.school_id,
        "create_faculty",
        outcome="success",
        detail={"display_name": row["display_name"], "faculty_role": row["faculty_role"]},
    )
    await db.commit()
    return SchoolFacultyResponse(**row)


@router.patch("/faculty/{faculty_id}", response_model=SchoolFacultyResponse)
async def update_school_faculty(
    faculty_id: str,
    body: SchoolFacultyUpdateRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "manage_faculty_registry")
    from app.services.school_faculty_registry import update_faculty

    ctx = _school_ctx()
    row = await update_faculty(
        db,
        ctx.school_id,
        faculty_id,
        display_name=body.display_name,
        faculty_role=body.faculty_role,
        subject=body.subject,
        email=body.email,
        notes=body.notes,
        is_active=body.is_active,
    )
    await _audit_school_action(
        db,
        user,
        ctx.school_id,
        "update_faculty",
        outcome="success",
        detail={"faculty_id": faculty_id},
    )
    await db.commit()
    return SchoolFacultyResponse(**row)


@router.patch("/students/{student_id}/faculty-assignments")
async def assign_student_faculty(
    student_id: str,
    body: SchoolStudentFacultyAssignRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "submit_enrollment")
    from app.services.school_faculty_registry import assign_faculty_to_student

    ctx = _school_ctx()
    res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.id == student_id,
            SchoolStudent.school_id == ctx.school_id,
        )
    )
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    out = await assign_faculty_to_student(
        db,
        ctx.school_id,
        student,
        class_teacher_faculty_id=body.class_teacher_faculty_id,
        mentor_faculty_id=body.mentor_faculty_id,
        clear_class_teacher=body.clear_class_teacher,
        clear_mentor=body.clear_mentor,
    )
    await _audit_school_action(
        db,
        user,
        ctx.school_id,
        "assign_student_faculty",
        student_id=student.id,
        outcome="success",
        detail=out,
    )
    await db.commit()
    return {"status": "success", **out}


@router.post("/students/sync-circle-links")
async def sync_student_circle_links(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Principal: refresh circle name + SL from live sponsor circles."""
    await _enforce_school_permission(db, user, "manage_faculty_registry")
    from app.services.school_circle_sync import backfill_circle_links_for_school

    ctx = _school_ctx()
    result = await backfill_circle_links_for_school(db, ctx.school_id)
    await _audit_school_action(
        db,
        user,
        ctx.school_id,
        "sync_circle_links",
        outcome="success",
        detail=result,
    )
    await db.commit()
    return {"status": "success", **result}


@router.post("/profile/school-photo", response_model=SchoolPhotoUploadResponse)
async def upload_school_photo(
    file: UploadFile = File(...),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db, user, "manage_profile_photos", audit_action="upload_school_logo"
    )
    profile.school_logo_url = await _upload_profile_image(file, "zenk/schools/logos")
    await _audit_school_action(db, user, profile.id, "upload_school_logo", outcome="success")
    await db.commit()
    await db.refresh(profile)
    return SchoolPhotoUploadResponse(url=profile.school_logo_url)


@router.post("/profile/principal-photo", response_model=SchoolPhotoUploadResponse)
async def upload_principal_photo(
    file: UploadFile = File(...),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db, user, "manage_profile_photos", audit_action="upload_principal_photo"
    )
    profile.principal_photo_url = await _upload_profile_image(file, "zenk/schools/principals")
    await _audit_school_action(db, user, profile.id, "upload_principal_photo", outcome="success")
    await db.commit()
    await db.refresh(profile)
    return SchoolPhotoUploadResponse(url=profile.principal_photo_url)


@router.get("/students", response_model=List[SchoolStudentResponse])
async def get_students(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    _school_ctx().profile
    res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == _school_id())
    )
    students = res.scalars().all()
    return [
        SchoolStudentResponse(
            id=s.id,
            full_name=s.full_name,
            grade=s.grade,
            circle_id=s.circle_id,
            circle_name=s.circle_name,
            attendance_pct=s.attendance_pct,
            avg_score=s.avg_score,
            zqa_score=s.zqa_score,
            risk_level=s.risk_level,
            q_report_status=s.q_report_status,
            tutor_recommendation=s.tutor_recommendation,
            tutor_recommendation_status=s.tutor_recommendation_status,
            zenk_id=s.zenk_id,
            dob=s.dob,
            class_teacher=s.class_teacher,
            class_teacher_faculty_id=s.class_teacher_faculty_id,
            sl_name=s.sl_name,
            mentor_name=s.mentor_name,
            mentor_faculty_id=s.mentor_faculty_id,
            rank_in_class=s.rank_in_class,
            class_size=s.class_size,
            zenq_contribution=s.zenq_contribution,
            zqa_baseline_delta=s.zqa_baseline_delta,
        )
        for s in students
    ]


@router.get("/student-interests")
async def school_student_interests(
    status: str = "pending_principal",
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v2: students who selected this school at signup and await principal approval."""
    await _enforce_school_permission(db, user, "submit_enrollment")
    return await list_principal_school_interests(db, _school_id(), status=status)


@router.post("/student-interests/{interest_id}/approve")
async def school_approve_student_interest(
    interest_id: str,
    body: ParentReviewRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "submit_enrollment")
    await _require_profile_complete(_school_ctx())
    return await approve_school_interest(
        db,
        interest_id=interest_id,
        school_id=_school_id(),
        principal=user,
        note=body.note,
    )


@router.post("/student-interests/{interest_id}/reject")
async def school_reject_student_interest(
    interest_id: str,
    body: ParentRejectRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "submit_enrollment")
    return await reject_school_interest(
        db,
        interest_id=interest_id,
        school_id=_school_id(),
        principal=user,
        note=body.note,
    )


@router.get("/pending-student-signups", response_model=List[PendingStudentSignupResponse])
async def school_pending_student_signups(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """KYC-approved ZenK student signups not yet admitted to this school."""
    profile = await _enforce_school_permission(db, user, "submit_enrollment")
    rows = await list_pending_student_signups(db, profile)
    return [PendingStudentSignupResponse(**r) for r in rows]


@router.post("/students/admit-signup", response_model=AdmitStudentSignupResponse)
async def school_admit_student_signup(
    body: AdmitStudentSignupRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    One-click admit: link an approved student signup to this school.
    Circle join is requested later from the student dashboard.
    """
    profile = await _enforce_school_permission(db, user, "submit_enrollment")
    ctx = _school_ctx()
    await _require_profile_complete(ctx)
    try:
        student = await admit_student_signup(
            db,
            school_id=profile.id,
            signup_id=body.signup_id.strip(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await _audit_school_action(
        db,
        user,
        profile.id,
        "admit_student_signup",
        student_id=student.id,
        detail={"signup_id": body.signup_id},
    )
    await db.commit()

    return AdmitStudentSignupResponse(
        status="success",
        message=(
            f"{student.full_name} is now enrolled at your school. "
            "They can request a sponsorship circle from their student dashboard."
        ),
        student_id=student.id,
        signup_id=body.signup_id,
    )


@router.get("/circles", response_model=List[SchoolCircleOption])
async def list_school_circles(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ZenK sponsor circles available for new student enrollment."""
    _require_school(user)
    return [SchoolCircleOption(**c) for c in await list_active_circles(db)]


@router.get("/enrollment-requests", response_model=List[SchoolEnrollmentRequestResponse])
async def list_school_enrollment_requests(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = _school_ctx().profile
    res = await db.execute(
        select(SchoolStudentEnrollmentRequest)
        .where(SchoolStudentEnrollmentRequest.school_id == _school_id())
        .order_by(SchoolStudentEnrollmentRequest.requested_at.desc())
    )
    return [
        SchoolEnrollmentRequestResponse(
            **enrollment_request_to_dict(r, school_name=profile.school_name)
        )
        for r in res.scalars().all()
    ]


@router.post("/enrollment-requests", response_model=SchoolEnrollmentCreateResponse)
async def submit_student_enrollment(
    body: SchoolStudentEnrollRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Propose a new student for a ZenK circle. Sends intimation to the circle;
    student record is created only after circle approval.
    """
    profile = await _enforce_school_permission(db, user, "submit_enrollment")

    payload = body.model_dump()
    if body.initial_academic_payload:
        ia = body.initial_academic_payload
        payload["initial_academic_payload"] = ia.model_dump()
        if ia.include_initial_report and ia.subject_scores and ia.blooms and ia.sel:
            validate_quarterly_payload(
                {
                    "attendance_pct": ia.attendance_pct,
                    "avg_score": ia.avg_score,
                    "subject_scores": ia.subject_scores.model_dump(),
                    "blooms": ia.blooms.model_dump(),
                    "sel": ia.sel.model_dump(),
                }
            )

    try:
        req = await create_enrollment_request(
            db, school_id=_school_id(), user=user, body=payload
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await _audit_school_action(
        db,
        user,
        profile.id,
        "submit_enrollment",
        outcome="success",
        detail={"enrollment_request_id": req.id, "circle_id": req.circle_id},
    )
    await db.commit()

    data = enrollment_request_to_dict(req, school_name=profile.school_name)
    return SchoolEnrollmentCreateResponse(
        status="success",
        message=(
            f"Enrollment request sent to {req.circle_name}. "
            "The circle will review and approve before the student appears on your dashboard."
        ),
        request=SchoolEnrollmentRequestResponse(**data),
    )


@router.get("/students/{student_id}", response_model=SchoolStudentDetailResponse)
async def get_student_detail(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    
    # 1. Get student
    res = await db.execute(select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == _school_id()))
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # 2. Get related data
    subject_res = await db.execute(select(SchoolStudentSubjectScore).where(SchoolStudentSubjectScore.student_id == student_id))
    blooms_res = await db.execute(select(SchoolStudentBloomsAssessment).where(SchoolStudentBloomsAssessment.student_id == student_id))
    sel_res = await db.execute(select(SchoolStudentSEL).where(SchoolStudentSEL.student_id == student_id))
    narrative_res = await db.execute(select(SchoolStudentNarrative).where(SchoolStudentNarrative.student_id == student_id))

    return SchoolStudentDetailResponse(
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
        class_teacher_faculty_id=student.class_teacher_faculty_id,
        sl_name=student.sl_name,
        mentor_name=student.mentor_name,
        mentor_faculty_id=student.mentor_faculty_id,
        rank_in_class=student.rank_in_class,
        class_size=student.class_size,
        zenq_contribution=student.zenq_contribution,
        zqa_baseline_delta=student.zqa_baseline_delta,
        subject_scores=[SchoolStudentSubjectScoreResponse(subject=s.subject, quarter=s.quarter, score=s.score) for s in subject_res.scalars()],
        blooms_assessments=[SchoolStudentBloomsAssessmentResponse(
            quarter=b.quarter, remember=b.remember, understand=b.understand, apply=b.apply, analyse=b.analyse, evaluate=b.evaluate, create=b.create, assessed_by=b.assessed_by
        ) for b in blooms_res.scalars()],
        sel_assessments=[SchoolStudentSELResponse(
            quarter=s.quarter, self_awareness=s.self_awareness, self_management=s.self_management, social_awareness=s.social_awareness, relationship_skills=s.relationship_skills, responsible_decisions=s.responsible_decisions
        ) for s in sel_res.scalars()],
        narratives=[SchoolStudentNarrativeResponse(
            quarter=n.quarter, teacher_name=n.teacher_name, narrative=n.narrative, finalized=n.finalized
        ) for n in narrative_res.scalars()]
    )


@router.delete("/students/{student_id}")
async def remove_student(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a student from the school dashboard (principal only). Cascades related records."""
    profile = await _enforce_school_permission(
        db,
        user,
        "remove_student",
        audit_action="remove_student",
        student_id=student_id,
    )
    res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.id == student_id,
            SchoolStudent.school_id == profile.id,
        )
    )
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student_name = student.full_name
    await db.delete(student)
    await _recalc_school_profile(db, profile.id)
    await _audit_school_action(
        db,
        user,
        profile.id,
        "remove_student",
        student_id=student_id,
        outcome="success",
        detail={"student_name": student_name},
    )
    await db.commit()
    return {
        "status": "success",
        "message": f"{student_name} was removed from your school dashboard.",
    }


@router.get("/students/{student_id}/zqa-breakdown")
async def get_student_zqa_breakdown(
    student_id: str,
    quarter: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    q = (quarter or "Q4").strip().upper()
    if q not in ("Q1", "Q2", "Q3", "Q4"):
        raise HTTPException(status_code=400, detail="Quarter must be Q1, Q2, Q3, or Q4.")

    stu_res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.id == student_id, SchoolStudent.school_id == _school_id()
        )
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return await get_zqa_breakdown(db, student, q)


@router.post("/students/{student_id}/recompute-zqa")
async def recompute_student_zqa(
    student_id: str,
    quarter: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = _school_ctx().profile
    q = (quarter or "Q4").strip().upper()
    if q not in ("Q1", "Q2", "Q3", "Q4"):
        raise HTTPException(status_code=400, detail="Quarter must be Q1, Q2, Q3, or Q4.")

    stu_res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.id == student_id, SchoolStudent.school_id == profile.id
        )
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    result = await recompute_and_apply_zqa(
        db,
        school_id=profile.id,
        student=student,
        quarter=q,
        finalized=True,
    )
    await db.commit()
    payload = result.to_breakdown_dict()
    payload["student_id"] = student.id
    payload["student_name"] = student.full_name
    return payload


@router.post("/students/{student_id}/request-meeting")
async def request_parent_meeting_student(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db,
        user,
        "request_meeting",
        audit_action="request_parent_meeting_student",
        student_id=student_id,
    )
    await _audit_school_action(
        db,
        user,
        profile.id,
        "request_parent_meeting_student",
        student_id=student_id,
        outcome="simulated",
    )
    await db.commit()
    return {
        "status": "simulated",
        "message": "Simulation only: parent meeting workflow is not yet integrated to scheduling/notification systems.",
    }

@router.post("/students/{student_id}/finalize-report")
async def finalize_student_report(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db,
        user,
        "finalize_report",
        audit_action="finalize_report",
        student_id=student_id,
    )
    # Verify the student belongs to this school
    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == _school_id())
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    # Mark narratives as finalized
    narrative_res = await db.execute(
        select(SchoolStudentNarrative).where(SchoolStudentNarrative.student_id == student_id)
    )
    narratives = narrative_res.scalars().all()
    if not narratives:
        raise HTTPException(status_code=404, detail="No narratives found for this student.")

    already_finalized = all(n.finalized for n in narratives)
    if already_finalized:
        return {"status": "already_done", "message": f"Report for {student.full_name} was already finalized."}

    for n in narratives:
        n.finalized = True
    await _audit_school_action(
        db,
        user,
        profile.id,
        "finalize_report",
        student_id=student_id,
        outcome="success",
    )
    await db.commit()
    return {
        "status": "success",
        "message": f"Report for {student.full_name} has been finalized and distributed to Sponsor Lead and Mentor.",
        "student_name": student.full_name,
    }


@router.get("/students/{student_id}/preview-report")
async def preview_student_report(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a text-based report preview from the student's data."""
    _require_school(user)
    profile = _school_ctx().profile

    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == _school_id())
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    # Fetch all related data
    scores_res = await db.execute(
        select(SchoolStudentSubjectScore).where(SchoolStudentSubjectScore.student_id == student_id)
    )
    scores = scores_res.scalars().all()

    blooms_res = await db.execute(
        select(SchoolStudentBloomsAssessment).where(SchoolStudentBloomsAssessment.student_id == student_id)
    )
    blooms = blooms_res.scalars().all()

    sel_res = await db.execute(
        select(SchoolStudentSEL).where(SchoolStudentSEL.student_id == student_id)
    )
    sels = sel_res.scalars().all()

    narrative_res = await db.execute(
        select(SchoolStudentNarrative).where(SchoolStudentNarrative.student_id == student_id)
    )
    narratives = narrative_res.scalars().all()

    # Build the preview text
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  ZENK STUDENT PROGRESS REPORT")
    lines.append(f"  {profile.school_name} — {profile.fy_current}")
    lines.append(f"{'='*60}")
    lines.append(f"")
    lines.append(f"  Student: {student.full_name}")
    lines.append(f"  ZenK ID: {student.zenk_id or 'N/A'}")
    lines.append(f"  Grade: {student.grade}")
    lines.append(f"  Circle: {student.circle_name or 'Unassigned'}")
    lines.append(f"  Class Teacher: {student.class_teacher or 'N/A'}")
    lines.append(f"  Sponsor Lead: {student.sl_name or 'N/A'}")
    lines.append(f"  Mentor: {student.mentor_name or 'Not assigned'}")
    lines.append(f"")
    lines.append(f"{'─'*60}")
    lines.append(f"  KEY METRICS")
    lines.append(f"{'─'*60}")
    lines.append(f"  Attendance:        {student.attendance_pct}%")
    lines.append(f"  Average Score:     {student.avg_score}%")
    zqa_line = f"{student.zqa_score}%" if student.zqa_score > 0 else "Pending (ZenK calculation)"
    lines.append(f"  ZQA Score:         {zqa_line}")
    lines.append(f"  Class Rank:        {student.rank_in_class or 'N/A'} / {student.class_size or 'N/A'}")
    lines.append(f"  ZenQ Contribution: +{student.zenq_contribution or 0}")
    lines.append(f"  Risk Level:        {student.risk_level}")
    lines.append(f"")

    if scores:
        lines.append(f"{'─'*60}")
        lines.append(f"  SUBJECT PERFORMANCE (QUARTERLY)")
        lines.append(f"{'─'*60}")
        grouped = {}
        for s in scores:
            grouped.setdefault(s.subject, {})[s.quarter] = s.score
        for subject, quarters in grouped.items():
            q_str = "  |  ".join([f"{q}: {v}" for q, v in sorted(quarters.items())])
            lines.append(f"  {subject}:  {q_str}")
        lines.append(f"")

    if blooms:
        b = blooms[0]
        lines.append(f"{'─'*60}")
        lines.append(f"  BLOOM'S TAXONOMY ({b.quarter})")
        lines.append(f"{'─'*60}")
        lines.append(f"  Remember: {b.remember}  |  Understand: {b.understand}  |  Apply: {b.apply}")
        lines.append(f"  Analyse: {b.analyse}  |  Evaluate: {b.evaluate}  |  Create: {b.create}")
        lines.append(f"  Assessed by: {b.assessed_by or 'N/A'}")
        lines.append(f"")

    if sels:
        sel = sels[0]
        lines.append(f"{'─'*60}")
        lines.append(f"  SOCIAL-EMOTIONAL LEARNING ({sel.quarter})")
        lines.append(f"{'─'*60}")
        lines.append(f"  Self-Awareness: {sel.self_awareness}/5  |  Self-Management: {sel.self_management}/5")
        lines.append(f"  Social Awareness: {sel.social_awareness}/5  |  Relationship Skills: {sel.relationship_skills}/5")
        lines.append(f"  Responsible Decisions: {sel.responsible_decisions}/5")
        lines.append(f"")

    if narratives:
        n = narratives[0]
        lines.append(f"{'─'*60}")
        lines.append(f"  TEACHER NARRATIVE ({n.quarter}) — {n.teacher_name}")
        lines.append(f"{'─'*60}")
        lines.append(f"  {n.narrative}")
        lines.append(f"")
        lines.append(f"  Finalized: {'Yes' if n.finalized else 'No'}")
        lines.append(f"")

    lines.append(f"{'='*60}")
    lines.append(f"  Generated by ZenK Impact Platform — Kia AI")
    lines.append(f"{'='*60}")

    report_text = "\n".join(lines)

    return {
        "status": "success",
        "student_name": student.full_name,
        "report_text": report_text,
    }


@router.post("/students/{student_id}/notify-sl")
async def notify_sponsor_lead(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a notification to the Sponsor Lead about this student's report."""
    profile = await _enforce_school_permission(
        db,
        user,
        "notify_sl",
        audit_action="notify_sponsor_lead",
        student_id=student_id,
    )

    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == _school_id())
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    sl_name = student.sl_name or "Sponsor Lead"
    notification_message = (
        f"Hi {sl_name}, this is an automated notification from {profile.school_name}. "
        f"The academic report for {student.full_name} ({student.grade}, Circle: {student.circle_name or 'N/A'}) "
        f"is ready for your review. "
        f"Key metrics — Attendance: {student.attendance_pct}%, Avg Score: {student.avg_score}%, "
        f"Risk Level: {student.risk_level}. "
        f"Please log in to the ZenK platform to review the full report."
    )

    await _audit_school_action(
        db,
        user,
        profile.id,
        "notify_sponsor_lead",
        student_id=student_id,
        outcome="simulated",
    )
    await db.commit()
    return {
        "status": "simulated",
        "message": f"Simulation only: notification preview generated for {sl_name}. Delivery integration is not enabled yet.",
        "sl_name": sl_name,
        "notification_preview": notification_message,
    }


@router.get("/reports", response_model=List[SchoolReportResponse])
async def get_reports(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    _school_ctx().profile

    reports_res = await db.execute(
        select(SchoolReport).where(SchoolReport.school_id == _school_id())
    )
    reports = reports_res.scalars().all()

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == _school_id())
    )
    student_map = {s.id: s.full_name for s in students_res.scalars().all()}

    return [
        SchoolReportResponse(
            id=r.id,
            student_id=r.student_id,
            student_name=student_map.get(r.student_id, "Unknown"),
            quarter=r.quarter,
            fy=r.fy,
            submitted_at=r.submitted_at.isoformat() if r.submitted_at else None,
            kia_draft=r.kia_draft,
            status=r.status,
        )
        for r in reports
    ]


@router.patch("/reports/{report_id}/submit")
async def submit_report(
    report_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    res = await db.execute(
        select(SchoolReport).where(
            SchoolReport.id == report_id,
            SchoolReport.school_id == _school_id(),
        )
    )
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    report.status = "Submitted"
    report.submitted_at = datetime.utcnow()

    profile = _school_ctx().profile
    if profile.reports_pending > 0:
        profile.reports_pending -= 1

    await db.commit()
    return {"ok": True}


@router.post("/academic-reports/generate-all")
async def generate_all_reports(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    return {
        "status": "success",
        "message": "Reports come from Submit report form data only. Open Submit report to enter quarterly metrics.",
    }

@router.post("/academic-reports/download-all")
async def download_all_reports(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db, user, "download_all_reports", audit_action="download_all_reports"
    )
    await _audit_school_action(
        db, user, profile.id, "download_all_reports", outcome="simulated"
    )
    await db.commit()
    return {
        "status": "simulated",
        "message": "Simulation only: bulk ZIP export email delivery is not integrated yet.",
    }


from pydantic import BaseModel as PydanticBaseModel

class NarrativeUpdateRequest(PydanticBaseModel):
    narrative: str
    quarter: str = "Q4"

@router.patch("/academic-reports/{student_id}/narrative")
async def update_student_narrative(
    student_id: str,
    body: NarrativeUpdateRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the narrative text for a student's quarterly report."""
    _require_school(user)
    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == _school_id())
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    narrative_res = await db.execute(
        select(SchoolStudentNarrative).where(
            SchoolStudentNarrative.student_id == student_id,
            SchoolStudentNarrative.quarter == body.quarter,
        )
    )
    narrative = narrative_res.scalar_one_or_none()
    if narrative:
        narrative.narrative = body.narrative
    else:
        import uuid
        db.add(SchoolStudentNarrative(
            id=str(uuid.uuid4()),
            student_id=student_id,
            quarter=body.quarter,
            teacher_name=student.class_teacher or "Teacher",
            narrative=body.narrative,
            finalized=False,
        ))
    await db.commit()
    return {"status": "success", "message": f"Narrative updated for {student.full_name} ({body.quarter})."}


@router.post("/academic-reports/{student_id}/distribute")
async def distribute_student_report(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Distribute a finalized report to SL, Mentor, and Parents."""
    profile = await _enforce_school_permission(
        db,
        user,
        "distribute_report",
        audit_action="distribute_student_report",
        student_id=student_id,
    )
    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == _school_id())
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    sl_name = student.sl_name or "Sponsor Lead"
    mentor_name = student.mentor_name or "Mentor"
    await _audit_school_action(
        db,
        user,
        profile.id,
        "distribute_student_report",
        student_id=student_id,
        outcome="simulated",
    )
    await db.commit()
    return {
        "status": "simulated",
        "message": (
            f"Simulation only: distribution preview ready for {student.full_name} "
            f"to {sl_name}, {mentor_name}, and Parent."
        ),
    }


@router.post("/academic-reports/{student_id}/finalize-draft")
async def finalize_kia_draft(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Teacher approves Kia draft — marks narrative as finalized."""
    profile = await _enforce_school_permission(
        db,
        user,
        "finalize_kia_draft",
        audit_action="finalize_kia_draft",
        student_id=student_id,
    )
    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == _school_id())
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    narrative_res = await db.execute(
        select(SchoolStudentNarrative).where(
            SchoolStudentNarrative.student_id == student_id,
            SchoolStudentNarrative.quarter == "Q4",
        )
    )
    narrative = narrative_res.scalar_one_or_none()
    if not narrative:
        raise HTTPException(status_code=404, detail="No Q4 narrative found for this student.")

    if narrative.finalized:
        return {"status": "already_done", "message": f"Narrative for {student.full_name} was already finalized."}

    narrative.finalized = True
    await _audit_school_action(
        db,
        user,
        profile.id,
        "finalize_kia_draft",
        student_id=student_id,
        outcome="success",
    )
    await db.commit()
    return {"status": "success", "message": f"Kia draft for {student.full_name} approved and finalized."}

@router.get("/reports/import-guide")
async def download_import_guide(
    user: SignupRequest = Depends(get_current_user),
):
    """Plain-text guide for CSV, PDF, and form submission."""
    _require_school(user)
    return PlainTextResponse(
        import_guide_text(),
        headers={"Content-Disposition": 'attachment; filename="zenk_school_import_guide.txt"'},
    )


@router.get("/reports/pdf-template")
async def download_pdf_template(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Blank quarterly report PDF to fill and re-upload for AI extraction."""
    _require_school(user)
    profile = _school_ctx().profile
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == _school_id())
    )
    students = students_res.scalars().all()
    pdf_bytes = generate_blank_report_pdf(profile.school_name, students)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="zenk_quarterly_report_template.pdf"'
        },
    )


@router.get("/reports/csv-template")
async def download_csv_template(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download CSV template with headers and one example row for enrolled students."""
    _require_school(user)
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == _school_id())
    )
    students = students_res.scalars().all()
    content = csv_template_text(students)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="zenk_quarterly_report_template.csv"'
        },
    )


@router.post("/reports/pdf-extract", response_model=SchoolPdfExtractResponse)
async def extract_pdf_report(
    file: UploadFile = File(...),
    student_id: Optional[str] = Form(None),
    quarter: Optional[str] = Form(None),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload PDF → AI extract → pending review (not live until approved)."""
    await _enforce_school_permission(db, user, "import_pdf")

    if file.content_type and file.content_type not in _ALLOWED_PDF_TYPES:
        raise HTTPException(status_code=400, detail="File must be a PDF.")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are allowed.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > _MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="PDF must be <= 10 MB.")

    try:
        result = await process_pdf_upload(
            db,
            school_id=_school_id(),
            user=user,
            file_bytes=contents,
            filename=file.filename,
            student_id=student_id,
            quarter=quarter,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return SchoolPdfExtractResponse(**result)


@router.get("/reports/pending-reviews", response_model=List[SchoolPendingReviewResponse])
async def list_pending_reviews(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    res = await db.execute(
        select(SchoolFormSubmission)
        .where(
            SchoolFormSubmission.school_id == _school_id(),
            SchoolFormSubmission.status == "pending_review",
        )
        .order_by(SchoolFormSubmission.submitted_at.desc())
    )
    reviews = res.scalars().all()
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == _school_id())
    )
    name_map = {s.id: s.full_name for s in students_res.scalars().all()}

    out = []
    for r in reviews:
        pl = r.payload or {}
        extracted = pl.get("extracted") or {}
        out.append(
            SchoolPendingReviewResponse(
                id=r.id,
                student_id=r.student_id,
                student_name=name_map.get(r.student_id, "Unknown"),
                quarter=r.quarter,
                fy=r.fy,
                source=r.source,
                submitted_by_name=r.submitted_by_name,
                submitted_at=r.submitted_at.isoformat(),
                filename=pl.get("filename"),
                confidence=extracted.get("confidence"),
                notes=extracted.get("notes"),
                draft=pl.get("draft") or {},
            )
        )
    return out


@router.post("/reports/reviews/{review_id}/approve")
async def approve_review(
    review_id: str,
    body: SchoolReviewApproveRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db, user, "approve_pdf_review", audit_action="approve_pdf_review"
    )
    if body.risk_level not in ("Low", "Medium", "High"):
        raise HTTPException(status_code=400, detail="Risk level must be Low, Medium, or High.")
    try:
        payload = validate_quarterly_payload(body.model_dump())
        result = await approve_pdf_review(
            db,
            school_id=_school_id(),
            user=user,
            review_id=review_id,
            payload=payload,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await _audit_school_action(
        db,
        user,
        profile.id,
        "approve_pdf_review",
        student_id=result.get("student_id") if isinstance(result, dict) else None,
        outcome="success",
        detail={"review_id": review_id},
    )
    await db.commit()
    return result


@router.post("/reports/reviews/{review_id}/reject")
async def reject_review(
    review_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db, user, "reject_pdf_review", audit_action="reject_pdf_review"
    )
    res = await db.execute(
        select(SchoolFormSubmission).where(
            SchoolFormSubmission.id == review_id,
            SchoolFormSubmission.school_id == _school_id(),
            SchoolFormSubmission.status == "pending_review",
        )
    )
    review = res.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    review.status = "rejected"
    await _audit_school_action(
        db,
        user,
        profile.id,
        "reject_pdf_review",
        student_id=review.student_id,
        outcome="success",
        detail={"review_id": review_id},
    )
    await db.commit()
    return {"status": "success", "message": "Review discarded."}


@router.post("/reports/csv-import", response_model=SchoolCsvImportResponse)
async def import_csv_reports(
    file: UploadFile = File(...),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import quarterly reports from CSV (one row per student per quarter)."""
    profile = await _enforce_school_permission(db, user, "import_csv")

    if file.content_type and file.content_type not in _ALLOWED_CSV_TYPES:
        raise HTTPException(status_code=400, detail="File must be a CSV.")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are allowed.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=400, detail="CSV must be <= 2 MB.")

    try:
        result = await import_quarterly_csv(
            db, school_id=_school_id(), user=user, file_bytes=contents
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return SchoolCsvImportResponse(
        status=result["status"],
        message=result["message"],
        success_count=result["success_count"],
        errors=result["errors"],
        imported=[
            {
                "row": item["row"],
                "student_name": item["student_name"],
                "quarter": item["quarter"],
                "submission_id": item["submission_id"],
            }
            for item in result["imported"]
        ],
    )


@router.post("/reports/submit", response_model=QuarterlyReportSubmitResponse)
async def submit_quarterly_report(
    body: QuarterlyReportSubmitRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save quarterly report from in-app form; records submitter and timestamp."""
    profile = await _enforce_school_permission(db, user, "submit_quarterly_report")

    quarter = body.quarter.strip().upper()
    if quarter not in ("Q1", "Q2", "Q3", "Q4"):
        raise HTTPException(status_code=400, detail="Quarter must be Q1, Q2, Q3, or Q4.")
    if body.risk_level not in ("Low", "Medium", "High"):
        raise HTTPException(status_code=400, detail="Risk level must be Low, Medium, or High.")

    stu_res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.id == body.student_id,
            SchoolStudent.school_id == _school_id(),
        )
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found for this school.")

    payload = body.model_dump()
    payload["quarter"] = quarter
    try:
        if payload.get("ready_for_zenk", True):
            validate_quarterly_payload(payload)
        submission = await apply_quarterly_report(
            db,
            school_id=_school_id(),
            student=student,
            user=user,
            payload=payload,
            source="manual",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await _audit_school_action(
        db,
        user,
        profile.id,
        "submit_quarterly_report",
        student_id=student.id,
        outcome="success",
        detail={"quarter": quarter, "submission_id": submission.id},
    )
    await db.commit()

    return QuarterlyReportSubmitResponse(
        status="success",
        message=f"Report saved for {student.full_name} ({quarter}).",
        submission_id=submission.id,
        student_id=student.id,
        student_name=student.full_name,
        quarter=quarter,
        submitted_by_name=submission.submitted_by_name,
        submitted_by_email=submission.submitted_by_email,
        submitted_at=submission.submitted_at.isoformat(),
    )


@router.get("/submissions", response_model=List[SchoolFormSubmissionResponse])
async def list_form_submissions(
    quarter: Optional[str] = None,
    limit: int = 50,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    q = (
        select(SchoolFormSubmission)
        .where(
            SchoolFormSubmission.school_id == _school_id(),
            SchoolFormSubmission.status == "processed",
        )
        .order_by(SchoolFormSubmission.submitted_at.desc())
        .limit(min(limit, 200))
    )
    if quarter:
        q = q.where(SchoolFormSubmission.quarter == quarter.strip().upper())

    subs = (await db.execute(q)).scalars().all()
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == _school_id())
    )
    name_map = {s.id: s.full_name for s in students_res.scalars().all()}

    return [
        SchoolFormSubmissionResponse(
            id=sub.id,
            student_id=sub.student_id,
            student_name=name_map.get(sub.student_id, "Unknown"),
            quarter=sub.quarter,
            fy=sub.fy,
            source=sub.source,
            submitted_by_name=sub.submitted_by_name,
            submitted_by_email=sub.submitted_by_email,
            submitted_at=sub.submitted_at.isoformat(),
            status=sub.status,
        )
        for sub in subs
    ]


@router.get("/academic-reports")
async def get_academic_reports(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Serve rich data for the academic reports grid dashboard."""
    _require_school(user)

    # Get all students
    students_res = await db.execute(select(SchoolStudent).where(SchoolStudent.school_id == _school_id()))
    students = students_res.scalars().all()

    submission_lookup = await latest_submission_map(db, _school_id())

    scores_res = await db.execute(
        select(SchoolStudentSubjectScore).where(
            SchoolStudentSubjectScore.student_id.in_([s.id for s in students])
            if students
            else False
        )
    )
    all_scores = scores_res.scalars().all()

    narrative_res = await db.execute(
        select(SchoolStudentNarrative).where(
            SchoolStudentNarrative.student_id.in_([s.id for s in students])
            if students
            else False
        )
    )
    all_narratives = narrative_res.scalars().all()

    reports_res = await db.execute(
        select(SchoolReport).where(SchoolReport.school_id == _school_id())
    )
    report_map = {(r.student_id, r.quarter): r for r in reports_res.scalars().all()}

    score_map = {}
    for sc in all_scores:
        key = _SUBJECT_TO_KEY.get(sc.subject, sc.subject.lower())
        score_map.setdefault(sc.student_id, {}).setdefault(sc.quarter, {})[key] = int(sc.score)

    narrative_map = {}
    for n in all_narratives:
        narrative_map.setdefault(n.student_id, {})[n.quarter] = n

    results = []

    for s in students:
        quarters_with_data = set()
        for q in score_map.get(s.id, {}):
            if score_map[s.id][q]:
                quarters_with_data.add(q)
        quarters_with_data.update(narrative_map.get(s.id, {}).keys())
        for (sid, q) in submission_lookup:
            if sid == s.id:
                quarters_with_data.add(q)
        for (sid, q) in report_map:
            if sid == s.id:
                quarters_with_data.add(q)

        if not quarters_with_data:
            quarters_with_data = {"Q4"}

        for quarter in sorted(
            quarters_with_data,
            key=lambda q: _QUARTER_ORDER.get(q, 0),
            reverse=True,
        ):
            scores = dict(score_map.get(s.id, {}).get(quarter, {}))
            sub = submission_lookup.get((s.id, quarter))
            narr_obj = narrative_map.get(s.id, {}).get(quarter)
            report_row = report_map.get((s.id, quarter))
            has_scores = len(scores) > 0

            if report_row:
                status = "Finalized" if report_row.status == "Submitted" else "Pending"
            elif narr_obj:
                status = "Finalized" if narr_obj.finalized else "Pending"
            elif sub or has_scores:
                status = "Pending"
            else:
                status = "NotStarted"

            if narr_obj:
                narrative_text = f'"{narr_obj.narrative}"'
            elif status == "NotStarted":
                narrative_text = '"No report submitted yet. Use Submit report to enter quarterly data."'
            else:
                narrative_text = '"Report in progress — add a teacher narrative in Submit report."'

            if has_scores:
                avg_score = sum(scores.values()) / len(scores)
                letter_grade = "A" if avg_score >= 80 else ("B" if avg_score >= 70 else "C")
                overall_grade = f"{letter_grade} - {int(avg_score)}% avg"
                if status == "Pending":
                    overall_grade += " (draft)"
            else:
                overall_grade = "— not submitted"

            meta_code, quarter_label = _QUARTER_META.get(quarter, (f"{quarter} 2025-26", quarter))
            if status == "NotStarted":
                quarter_label = "AWAITING SUBMISSION"
            elif status == "Pending":
                quarter_label = "PENDING REVIEW"

            display_status = status
            if status == "Finalized" and quarter != "Q4":
                display_status = "Finalized_Past"

            results.append({
                "id": f"{s.id}-{quarter.lower()}",
                "student_id": s.id,
                "quarter_code": meta_code,
                "quarter_label": quarter_label,
                "status": display_status,
                "student_name": s.full_name,
                "circle_name": s.circle_name or "Unassigned",
                "class_teacher": s.class_teacher or "N/A",
                "grade": s.grade,
                "scores": scores,
                "overall_grade": overall_grade,
                "zqa_score": s.zqa_score,
                "zqa_baseline_delta": s.zqa_baseline_delta,
                "narrative": narrative_text,
                "submitted_by_name": sub.submitted_by_name if sub else None,
                "submitted_by_email": sub.submitted_by_email if sub else None,
                "submitted_at": sub.submitted_at.isoformat() if sub else None,
                "submission_source": sub.source if sub else None,
                "access": [
                    {"role": "Teacher", "state": "checked"},
                    {"role": "Principal", "state": "checked"},
                    {"role": "Parent", "state": "checked"},
                    {"role": "SL (summary)", "state": "partial"},
                    {"role": "Mentor", "state": "checked"},
                ]
                if display_status in ("Finalized", "Finalized_Past")
                else None,
            })

    results.sort(
        key=lambda x: (_QUARTER_ORDER.get((x.get("quarter_code") or "Q0").split()[0], 0), x["student_name"]),
        reverse=True,
    )
    return results


@router.post("/attendance/{student_id}/request-meeting")
async def request_parent_meeting_attendance(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db,
        user,
        "request_meeting",
        audit_action="request_parent_meeting_attendance",
        student_id=student_id,
    )
    await _audit_school_action(
        db,
        user,
        profile.id,
        "request_parent_meeting_attendance",
        student_id=student_id,
        outcome="simulated",
    )
    await db.commit()
    return {
        "status": "simulated",
        "message": "Simulation only: parent meeting request was recorded locally; external workflow not integrated yet.",
    }

@router.post("/attendance/{student_id}/alert-sl")
async def alert_sl_attendance(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _enforce_school_permission(
        db,
        user,
        "alert_sl_attendance",
        audit_action="alert_sl_attendance",
        student_id=student_id,
    )
    await _audit_school_action(
        db,
        user,
        profile.id,
        "alert_sl_attendance",
        student_id=student_id,
        outcome="simulated",
    )
    await db.commit()
    return {
        "status": "simulated",
        "message": "Simulation only: Sponsor Lead alert channel is not integrated yet.",
    }


@router.get("/attendance/csv-template")
async def download_attendance_csv_template(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CSV template: one row per student per month (Apr 2025–Mar 2026)."""
    _require_school(user)
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == _school_id())
    )
    content = attendance_csv_template(students_res.scalars().all())
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="zenk_monthly_attendance_template.csv"'
        },
    )


@router.post("/attendance/csv-import", response_model=SchoolAttendanceImportResponse)
async def import_attendance_csv_upload(
    file: UploadFile = File(...),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload monthly attendance rows; recalculates student annual % and school average."""
    await _enforce_school_permission(db, user, "manage_attendance")

    if file.content_type and file.content_type not in _ALLOWED_CSV_TYPES:
        raise HTTPException(status_code=400, detail="File must be a CSV.")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are allowed.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=400, detail="CSV must be <= 2 MB.")

    try:
        result = await import_attendance_csv(
            db, school_id=_school_id(), user=user, file_bytes=contents
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return SchoolAttendanceImportResponse(**result)


@router.post("/attendance/entry", response_model=SchoolAttendanceEntryResponse)
async def save_attendance_entry_route(
    body: SchoolAttendanceEntryRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save one month: working_days + days_present; attendance % is calculated."""
    await _enforce_school_permission(db, user, "manage_attendance")

    try:
        record = await save_attendance_entry(
            db,
            school_id=_school_id(),
            student_id=body.student_id,
            month=body.month,
            year=body.year,
            working_days=body.working_days,
            days_present=body.days_present,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    st_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == body.student_id)
    )
    student = st_res.scalar_one_or_none()
    name = student.full_name if student else "Unknown"

    rec = SchoolAttendanceResponse(
        student_id=record.student_id,
        student_name=name,
        month=record.month,
        year=record.year,
        attendance_pct=record.attendance_pct,
        working_days=record.working_days,
        days_present=record.days_present,
    )
    return SchoolAttendanceEntryResponse(
        status="success",
        message=(
            f"Saved {name} — "
            f"{record.days_present}/{record.working_days} days "
            f"({record.attendance_pct}%)"
        ),
        record=rec,
    )


@router.get("/attendance", response_model=List[SchoolAttendanceResponse])
async def get_attendance(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    _school_ctx().profile

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == _school_id())
    )
    students = students_res.scalars().all()
    student_map = {s.id: s.full_name for s in students}
    student_ids = list(student_map.keys())

    if not student_ids:
        return []

    att_res = await db.execute(
        select(SchoolAttendance).where(SchoolAttendance.student_id.in_(student_ids))
    )
    records = att_res.scalars().all()

    return [
        SchoolAttendanceResponse(
            student_id=r.student_id,
            student_name=student_map.get(r.student_id, "Unknown"),
            month=r.month,
            year=r.year,
            attendance_pct=r.attendance_pct,
            working_days=r.working_days,
            days_present=r.days_present,
        )
        for r in records
    ]


@router.get("/zqa", response_model=List[SchoolZQAStudentResponse])
async def get_zqa(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    _school_ctx().profile

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == _school_id())
    )
    students = students_res.scalars().all()

    att_res = await db.execute(
        select(SchoolAttendance).where(
            SchoolAttendance.student_id.in_([s.id for s in students])
        )
    )
    all_att = att_res.scalars().all()

    att_by_student: dict[str, list] = {}
    for a in all_att:
        att_by_student.setdefault(a.student_id, []).append(a.attendance_pct)

    return [
        SchoolZQAStudentResponse(
            student_id=s.id,
            student_name=s.full_name,
            grade=s.grade,
            circle_name=s.circle_name,
            zqa_score=s.zqa_score,
            risk_level=s.risk_level,
            trend=att_by_student.get(s.id, [s.zqa_score]),
        )
        for s in students
    ]


@router.get("/kia-priorities", response_model=SchoolKiaPrioritiesResponse)
async def get_kia_priorities(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = _school_ctx().profile

    hour = datetime.utcnow().hour
    greeting_time = "morning" if hour < 12 else ("afternoon" if hour < 17 else "evening")
    greeting = f"Good {greeting_time}, {profile.principal_name}. Here are your priority actions for today."

    raw_items = await generate_school_priorities(_school_id(), db)
    items = [SchoolKiaPriorityItem(**item) for item in raw_items]

    return SchoolKiaPrioritiesResponse(greeting=greeting, items=items)


@router.post("/kia-chat", response_model=SchoolKiaChatResponse)
async def kia_chat(
    body: SchoolKiaChatRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = _school_ctx().profile

    user_msg = SchoolKiaMessage(
        school_id=profile.id,
        role="user",
        text=body.message,
    )
    db.add(user_msg)
    await db.flush()

    context = await fetch_school_context(_school_id(), db)
    reply = await generate_school_response(body.message, context)

    if not reply:
        raise HTTPException(status_code=503, detail="Kia is temporarily unavailable. Please try again shortly.")

    kia_msg = SchoolKiaMessage(school_id=profile.id, role="kia", text=reply)
    db.add(kia_msg)
    await db.commit()

    return SchoolKiaChatResponse(
        reply=reply,
        user_message_id=user_msg.id,
        kia_message_id=kia_msg.id,
    )


@router.delete("/kia-chat/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kia_message(
    message_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = _school_ctx().profile

    res = await db.execute(
        select(SchoolKiaMessage).where(
            SchoolKiaMessage.id == message_id,
            SchoolKiaMessage.school_id == profile.id,
        )
    )
    msg = res.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.role != "user":
        raise HTTPException(status_code=403, detail="Only your messages can be deleted")

    await db.delete(msg)
    await db.commit()


@router.get("/kia-chat/history", response_model=List[SchoolKiaMessageResponse])
async def get_kia_history(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = _school_ctx().profile

    res = await db.execute(
        select(SchoolKiaMessage)
        .where(SchoolKiaMessage.school_id == profile.id)
        .order_by(SchoolKiaMessage.created_at)
    )
    messages = res.scalars().all()

    return [
        SchoolKiaMessageResponse(
            id=m.id,
            school_id=m.school_id,
            role=m.role,
            text=m.text,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


_DEFAULT_KIA_WELCOME_TASKS = [
    "Review your student roster on the Students tab",
    "Submit a quarterly report (Submit report → Web form or CSV)",
    "Enter monthly attendance (Attendance tab — click a month or upload CSV)",
]


async def _ensure_kia_welcome(db: AsyncSession, school_id: str) -> SchoolKiaWelcome:
    res = await db.execute(
        select(SchoolKiaWelcome).where(SchoolKiaWelcome.id == school_id)
    )
    welcome = res.scalar_one_or_none()
    if welcome:
        return welcome

    welcome = SchoolKiaWelcome(
        id=school_id,
        welcome_sent=False,
        welcome_message=(
            "Welcome to your ZenK School Dashboard. Kia helps you track attendance, "
            "quarterly reports, and student progress in one place."
        ),
        task_list=_DEFAULT_KIA_WELCOME_TASKS,
    )
    db.add(welcome)
    await db.commit()
    await db.refresh(welcome)
    return welcome


@router.get("/kia-welcome", response_model=SchoolKiaWelcomeResponse)
async def get_kia_welcome(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = _school_ctx().profile
    welcome = await _ensure_kia_welcome(db, profile.id)

    tasks = welcome.task_list or []
    if tasks and isinstance(tasks[0], dict):
        tasks = [t.get("text", str(t)) for t in tasks]

    return SchoolKiaWelcomeResponse(
        id=welcome.id,
        welcome_sent=welcome.welcome_sent,
        welcome_message=welcome.welcome_message or "",
        task_list=tasks,
    )


@router.post("/kia-welcome/complete")
async def complete_kia_welcome(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark the one-time Kia welcome checklist as done."""
    _require_school(user)
    profile = _school_ctx().profile
    welcome = await _ensure_kia_welcome(db, profile.id)
    welcome.welcome_sent = True
    await db.commit()
    return {"status": "success", "message": "Welcome checklist completed."}


@router.post("/kia-recommend/{student_id}")
async def handle_tutor_recommendation(
    student_id: str,
    body: TutorRecommendationAction,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    _school_ctx().profile

    if body.action not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'reject'.")

    res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.id == student_id,
            SchoolStudent.school_id == _school_id(),
        )
    )
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    student.tutor_recommendation_status = body.action
    await db.commit()
    return {"ok": True, "status": body.action}


@router.get("/parent-submissions", response_model=List[SchoolParentSubmissionOut])
async def school_parent_submissions(
    status: str = "pending_principal",
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Principal queue for parent-uploaded marksheets and transcripts."""
    await _enforce_school_permission(db, user, "review_parent_upload", audit_action="list_parent_submissions")
    rows = await list_school_parent_submissions(db, _school_id(), status=status)
    return [SchoolParentSubmissionOut(**r) for r in rows]


@router.post("/parent-submissions/{submission_id}/approve", response_model=SchoolParentSubmissionOut)
async def school_approve_parent_submission(
    submission_id: str,
    body: ParentReviewRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(
        db,
        user,
        "review_parent_upload",
        audit_action="approve_parent_submission",
    )
    row = await approve_parent_submission(
        db,
        school_user=user,
        school_id=_school_id(),
        submission_id=submission_id,
        note=body.note,
    )
    await _audit_school_action(
        db,
        user,
        _school_id(),
        "approve_parent_submission",
        student_id=row.get("school_student_id"),
        detail={"submission_id": submission_id},
    )
    await db.commit()
    return SchoolParentSubmissionOut(**row)


@router.post("/parent-submissions/{submission_id}/reject", response_model=SchoolParentSubmissionOut)
async def school_reject_parent_submission(
    submission_id: str,
    body: ParentRejectRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(
        db,
        user,
        "review_parent_upload",
        audit_action="reject_parent_submission",
    )
    row = await reject_parent_submission(
        db,
        school_user=user,
        school_id=_school_id(),
        submission_id=submission_id,
        note=body.note,
    )
    await _audit_school_action(
        db,
        user,
        _school_id(),
        "reject_parent_submission",
        student_id=row.get("school_student_id"),
        detail={"submission_id": submission_id, "note": body.note},
    )
    await db.commit()
    return SchoolParentSubmissionOut(**row)


@router.get("/partner-circles", response_model=List[SchoolPartnerCircleResponse])
async def list_school_partner_circles(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sponsor circles with enrolled students from this school."""
    await _enforce_school_permission(db, user, "view_students")
    from app.services.circle_school_partner import list_partner_circles_for_school

    rows = await list_partner_circles_for_school(db, _school_id())
    return [SchoolPartnerCircleResponse(**r) for r in rows]


@router.get(
    "/partner-circles/{circle_id}/messages",
    response_model=List[SchoolPartnerMessageResponse],
)
async def list_school_partner_circle_messages(
    circle_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "view_students")
    from app.services.circle_school_partner import fetch_partner_messages

    school_id = _school_id()
    linked = await db.execute(
        select(func.count())
        .select_from(SchoolStudent)
        .where(
            SchoolStudent.school_id == school_id,
            SchoolStudent.circle_id == circle_id,
        )
    )
    if int(linked.scalar_one() or 0) < 1:
        raise HTTPException(status_code=404, detail="This circle is not linked to your school.")
    rows = await fetch_partner_messages(db, circle_id=circle_id, school_id=school_id)
    return [SchoolPartnerMessageResponse(**r) for r in rows]


@router.post(
    "/partner-circles/{circle_id}/messages",
    response_model=SchoolPartnerMessageResponse,
)
async def post_school_partner_circle_message(
    circle_id: str,
    body: SchoolPartnerMessageRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _enforce_school_permission(db, user, "view_students")
    from app.services.circle_school_partner import post_partner_message

    school_id = _school_id()
    linked = await db.execute(
        select(func.count())
        .select_from(SchoolStudent)
        .where(
            SchoolStudent.school_id == school_id,
            SchoolStudent.circle_id == circle_id,
        )
    )
    if int(linked.scalar_one() or 0) < 1:
        raise HTTPException(status_code=404, detail="This circle is not linked to your school.")
    try:
        row = await post_partner_message(
            db,
            circle_id=circle_id,
            school_id=school_id,
            sender_side="school",
            body=body.body,
            sender_signup=user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _audit_school_action(
        db,
        user,
        school_id,
        "partner_circle_message",
        detail={"circle_id": circle_id, "message_id": row["id"]},
    )
    await db.commit()
    return SchoolPartnerMessageResponse(**row)
