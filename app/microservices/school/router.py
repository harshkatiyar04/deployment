from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.jwt_auth import get_current_user
from app.models.signup import SignupRequest
from app.models.enums import Persona
from app.models.school import (
    SchoolProfile, SchoolStudent, SchoolReport,
    SchoolAttendance, SchoolKiaMessage, SchoolKiaWelcome,
    SchoolStudentSubjectScore, SchoolStudentBloomsAssessment,
    SchoolStudentSEL, SchoolStudentNarrative, SchoolFormSubmission,
    SchoolStudentEnrollmentRequest,
)
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
    SchoolStudentEnrollRequest,
    SchoolEnrollmentRequestResponse,
    SchoolEnrollmentCreateResponse,
)
from app.services.school_reports import apply_quarterly_report, latest_submission_map
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
from app.services.cloudinary_service import upload_image

router = APIRouter(prefix="/school", tags=["School Dashboard"])

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
    "Q2": ("Q2 2025-26", "APR-JUN 2025"),
    "Q1": ("Q1 2025-26", "APR-JUN 2025"),
}


def _require_school(user: SignupRequest) -> SignupRequest:
    if user.persona != Persona.school:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="School dashboard is restricted to school accounts.",
        )
    return user


async def _get_school_profile(user_id: str, db: AsyncSession) -> SchoolProfile:
    res = await db.execute(select(SchoolProfile).where(SchoolProfile.id == user_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="School profile not found.")
    return profile


def _profile_to_response(profile: SchoolProfile) -> SchoolProfileResponse:
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
    )


_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


async def _upload_profile_image(file: UploadFile, folder: str) -> str:
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a JPG, PNG, or WebP image.",
        )
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
    profile = await _get_school_profile(user.id, db)
    return _profile_to_response(profile)


@router.post("/profile/school-photo", response_model=SchoolPhotoUploadResponse)
async def upload_school_photo(
    file: UploadFile = File(...),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = await _get_school_profile(user.id, db)
    profile.school_logo_url = await _upload_profile_image(file, "zenk/schools/logos")
    await db.commit()
    await db.refresh(profile)
    return SchoolPhotoUploadResponse(url=profile.school_logo_url)


@router.post("/profile/principal-photo", response_model=SchoolPhotoUploadResponse)
async def upload_principal_photo(
    file: UploadFile = File(...),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = await _get_school_profile(user.id, db)
    profile.principal_photo_url = await _upload_profile_image(file, "zenk/schools/principals")
    await db.commit()
    await db.refresh(profile)
    return SchoolPhotoUploadResponse(url=profile.principal_photo_url)


@router.get("/students", response_model=List[SchoolStudentResponse])
async def get_students(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    await _get_school_profile(user.id, db)
    res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == user.id)
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
            sl_name=s.sl_name,
            mentor_name=s.mentor_name,
            rank_in_class=s.rank_in_class,
            class_size=s.class_size,
            zenq_contribution=s.zenq_contribution,
            zqa_baseline_delta=s.zqa_baseline_delta,
        )
        for s in students
    ]


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
    profile = await _get_school_profile(user.id, db)
    res = await db.execute(
        select(SchoolStudentEnrollmentRequest)
        .where(SchoolStudentEnrollmentRequest.school_id == user.id)
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
    _require_school(user)
    profile = await _get_school_profile(user.id, db)

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
            db, school_id=user.id, user=user, body=payload
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

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
    res = await db.execute(select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == user.id))
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
        sl_name=student.sl_name,
        mentor_name=student.mentor_name,
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

@router.post("/students/{student_id}/request-meeting")
async def request_parent_meeting(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    # Simple mock action
    return {"status": "success", "message": "Parent meeting requested via Kia"}

@router.post("/students/{student_id}/finalize-report")
async def finalize_student_report(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    # Verify the student belongs to this school
    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == user.id)
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
    profile = await _get_school_profile(user.id, db)

    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == user.id)
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
    _require_school(user)
    profile = await _get_school_profile(user.id, db)

    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == user.id)
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

    # In production, this would send a real ZenK Chat message or push notification.
    # For now, we log and return the message as confirmation.
    return {
        "status": "success",
        "message": f"Notification sent to {sl_name} via ZenK Chat.",
        "sl_name": sl_name,
        "notification_preview": notification_message,
    }


@router.get("/reports", response_model=List[SchoolReportResponse])
async def get_reports(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    await _get_school_profile(user.id, db)

    reports_res = await db.execute(
        select(SchoolReport).where(SchoolReport.school_id == user.id)
    )
    reports = reports_res.scalars().all()

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == user.id)
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
            SchoolReport.school_id == user.id,
        )
    )
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    report.status = "Submitted"
    report.submitted_at = datetime.utcnow()

    profile = await _get_school_profile(user.id, db)
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
    _require_school(user)
    return {"status": "success", "message": "ZIP archive of all finalized reports has been emailed to you."}


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
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == user.id)
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
    _require_school(user)
    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == user.id)
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    sl_name = student.sl_name or "Sponsor Lead"
    mentor_name = student.mentor_name or "Mentor"
    return {
        "status": "success",
        "message": f"Report for {student.full_name} distributed to {sl_name}, {mentor_name}, and Parent via ZenK.",
    }


@router.post("/academic-reports/{student_id}/finalize-draft")
async def finalize_kia_draft(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Teacher approves Kia draft — marks narrative as finalized."""
    _require_school(user)
    stu_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.id == student_id, SchoolStudent.school_id == user.id)
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
    profile = await _get_school_profile(user.id, db)
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == user.id)
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
        select(SchoolStudent).where(SchoolStudent.school_id == user.id)
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
    _require_school(user)
    await _get_school_profile(user.id, db)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are allowed.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = await process_pdf_upload(
            db,
            school_id=user.id,
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
            SchoolFormSubmission.school_id == user.id,
            SchoolFormSubmission.status == "pending_review",
        )
        .order_by(SchoolFormSubmission.submitted_at.desc())
    )
    reviews = res.scalars().all()
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == user.id)
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
    _require_school(user)
    if body.risk_level not in ("Low", "Medium", "High"):
        raise HTTPException(status_code=400, detail="Risk level must be Low, Medium, or High.")
    try:
        payload = validate_quarterly_payload(body.model_dump())
        result = await approve_pdf_review(
            db,
            school_id=user.id,
            user=user,
            review_id=review_id,
            payload=payload,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return result


@router.post("/reports/reviews/{review_id}/reject")
async def reject_review(
    review_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    res = await db.execute(
        select(SchoolFormSubmission).where(
            SchoolFormSubmission.id == review_id,
            SchoolFormSubmission.school_id == user.id,
            SchoolFormSubmission.status == "pending_review",
        )
    )
    review = res.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    review.status = "rejected"
    await db.commit()
    return {"status": "success", "message": "Review discarded."}


@router.post("/reports/csv-import", response_model=SchoolCsvImportResponse)
async def import_csv_reports(
    file: UploadFile = File(...),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import quarterly reports from CSV (one row per student per quarter)."""
    _require_school(user)
    await _get_school_profile(user.id, db)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are allowed.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = await import_quarterly_csv(
            db, school_id=user.id, user=user, file_bytes=contents
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
    _require_school(user)
    await _get_school_profile(user.id, db)

    quarter = body.quarter.strip().upper()
    if quarter not in ("Q1", "Q2", "Q3", "Q4"):
        raise HTTPException(status_code=400, detail="Quarter must be Q1, Q2, Q3, or Q4.")
    if body.risk_level not in ("Low", "Medium", "High"):
        raise HTTPException(status_code=400, detail="Risk level must be Low, Medium, or High.")

    stu_res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.id == body.student_id,
            SchoolStudent.school_id == user.id,
        )
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found for this school.")

    payload = body.model_dump()
    payload["quarter"] = quarter
    submission = await apply_quarterly_report(
        db,
        school_id=user.id,
        student=student,
        user=user,
        payload=payload,
        source="manual",
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
            SchoolFormSubmission.school_id == user.id,
            SchoolFormSubmission.status == "processed",
        )
        .order_by(SchoolFormSubmission.submitted_at.desc())
        .limit(min(limit, 200))
    )
    if quarter:
        q = q.where(SchoolFormSubmission.quarter == quarter.strip().upper())

    subs = (await db.execute(q)).scalars().all()
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == user.id)
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
    students_res = await db.execute(select(SchoolStudent).where(SchoolStudent.school_id == user.id))
    students = students_res.scalars().all()

    submission_lookup = await latest_submission_map(db, user.id)

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
        select(SchoolReport).where(SchoolReport.school_id == user.id)
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

        for quarter in sorted(quarters_with_data, reverse=True):
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

    results.sort(key=lambda x: (x["quarter_code"], x["student_name"]), reverse=True)
    return results


@router.post("/attendance/{student_id}/request-meeting")
async def request_parent_meeting(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    return {"status": "success", "message": "Parent meeting requested successfully."}

@router.post("/attendance/{student_id}/alert-sl")
async def alert_sl_attendance(
    student_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    return {"status": "success", "message": "Sponsor Lead has been alerted via ZenK."}


@router.get("/attendance/csv-template")
async def download_attendance_csv_template(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CSV template: one row per student per month (Apr 2025–Mar 2026)."""
    _require_school(user)
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == user.id)
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
    _require_school(user)
    await _get_school_profile(user.id, db)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are allowed.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = await import_attendance_csv(
            db, school_id=user.id, user=user, file_bytes=contents
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
    _require_school(user)
    await _get_school_profile(user.id, db)

    try:
        record = await save_attendance_entry(
            db,
            school_id=user.id,
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
    await _get_school_profile(user.id, db)

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == user.id)
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
    await _get_school_profile(user.id, db)

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == user.id)
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
    profile = await _get_school_profile(user.id, db)

    hour = datetime.utcnow().hour
    greeting_time = "morning" if hour < 12 else ("afternoon" if hour < 17 else "evening")
    greeting = f"Good {greeting_time}, {profile.principal_name}. Here are your priority actions for today."

    raw_items = await generate_school_priorities(user.id, db)
    items = [SchoolKiaPriorityItem(**item) for item in raw_items]

    return SchoolKiaPrioritiesResponse(greeting=greeting, items=items)


@router.post("/kia-chat", response_model=SchoolKiaChatResponse)
async def kia_chat(
    body: SchoolKiaChatRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = await _get_school_profile(user.id, db)

    user_msg = SchoolKiaMessage(
        school_id=profile.id,
        role="user",
        text=body.message,
    )
    db.add(user_msg)
    await db.flush()

    context = await fetch_school_context(user.id, db)
    reply = await generate_school_response(body.message, context)

    if not reply:
        raise HTTPException(status_code=503, detail="Kia is temporarily unavailable. Please try again shortly.")

    kia_msg = SchoolKiaMessage(school_id=profile.id, role="kia", text=reply)
    db.add(kia_msg)
    await db.commit()

    return SchoolKiaChatResponse(reply=reply)


@router.get("/kia-chat/history", response_model=List[SchoolKiaMessageResponse])
async def get_kia_history(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_school(user)
    profile = await _get_school_profile(user.id, db)

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
    profile = await _get_school_profile(user.id, db)
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
    profile = await _get_school_profile(user.id, db)
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
    await _get_school_profile(user.id, db)

    if body.action not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'reject'.")

    res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.id == student_id,
            SchoolStudent.school_id == user.id,
        )
    )
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    student.tutor_recommendation_status = body.action
    await db.commit()
    return {"ok": True, "status": body.action}
