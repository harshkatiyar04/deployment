"""Student onboarding v2 — school interest, circle interest, probe chat, timelines."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.gamified_persona import get_or_create_persona
from app.chat.models import CircleMember, SponsorCircle
from app.models.enums import KycStatus, Persona
from app.models.school import SchoolProfile, SchoolStudent
from app.models.signup import SignupRequest
from app.models.student_family import ParentAcademicSubmission, StudentFamilyLink
from app.models.student_onboarding import (
    StudentCircleInterestRequest,
    StudentProbeMessage,
    StudentSchoolInterest,
)
from app.services.family_circle_provision import provision_parent_after_student_enrollment
from app.services.school_student_admit import admit_student_signup
from app.services.student_dashboard import resolve_school_student

PROBE_DAYS = 7
ONBOARDING_V2 = "v2"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def list_public_schools(db: AsyncSession) -> list[dict[str, str]]:
    res = await db.execute(
        select(SchoolProfile)
        .where(SchoolProfile.is_partner.is_(True))
        .order_by(SchoolProfile.school_name)
    )
    return [
        {
            "id": s.id,
            "school_name": s.school_name,
            "city": s.city,
            "district": s.district,
            "affiliation": s.affiliation,
        }
        for s in res.scalars().all()
    ]


async def create_school_interest(
    db: AsyncSession,
    *,
    student_signup_id: str,
    school_id: str,
) -> StudentSchoolInterest:
    school_res = await db.execute(select(SchoolProfile).where(SchoolProfile.id == school_id))
    if not school_res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Selected school is not registered on ZenK")

    existing = await db.execute(
        select(StudentSchoolInterest).where(StudentSchoolInterest.student_signup_id == student_signup_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="School interest already recorded for this student")

    row = StudentSchoolInterest(
        student_signup_id=student_signup_id,
        school_id=school_id,
        status="pending_principal",
    )
    db.add(row)
    await db.flush()
    return row


async def list_principal_school_interests(
    db: AsyncSession,
    school_id: str,
    *,
    status: str = "pending_principal",
) -> list[dict[str, Any]]:
    q = (
        select(StudentSchoolInterest, SignupRequest)
        .join(SignupRequest, SignupRequest.id == StudentSchoolInterest.student_signup_id)
        .where(StudentSchoolInterest.school_id == school_id)
    )
    if status != "all":
        q = q.where(StudentSchoolInterest.status == status)
    q = q.order_by(StudentSchoolInterest.created_at.desc())
    res = await db.execute(q)
    rows = []
    for interest, signup in res.all():
        rows.append({
            "id": interest.id,
            "student_signup_id": signup.id,
            "full_name": signup.full_name,
            "grade": signup.grade_or_year,
            "email": signup.email,
            "kyc_status": signup.kyc_status.value,
            "status": interest.status,
            "created_at": interest.created_at.isoformat() if interest.created_at else None,
            "principal_note": interest.principal_note,
        })
    return rows


async def approve_school_interest(
    db: AsyncSession,
    *,
    interest_id: str,
    school_id: str,
    principal: SignupRequest,
    note: Optional[str] = None,
) -> dict[str, Any]:
    res = await db.execute(
        select(StudentSchoolInterest).where(
            StudentSchoolInterest.id == interest_id,
            StudentSchoolInterest.school_id == school_id,
        )
    )
    interest = res.scalar_one_or_none()
    if not interest:
        raise HTTPException(status_code=404, detail="School interest not found")
    if interest.status != "pending_principal":
        raise HTTPException(status_code=400, detail=f"Interest is already {interest.status}")

    stu_res = await db.execute(
        select(SignupRequest).where(SignupRequest.id == interest.student_signup_id)
    )
    student = stu_res.scalar_one_or_none()
    if not student or student.kyc_status != KycStatus.approved:
        raise HTTPException(status_code=400, detail="Student ZenK KYC must be approved before school admission")

    try:
        school_student = await admit_student_signup(
            db, school_id=school_id, signup_id=interest.student_signup_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    interest.status = "approved"
    interest.school_student_id = school_student.id
    interest.principal_note = (note or "").strip() or None
    interest.reviewed_by = principal.id
    interest.reviewed_at = _utcnow()
    interest.updated_at = _utcnow()
    await db.commit()

    return {
        "status": "approved",
        "school_student_id": school_student.id,
        "student_signup_id": interest.student_signup_id,
    }


async def reject_school_interest(
    db: AsyncSession,
    *,
    interest_id: str,
    school_id: str,
    principal: SignupRequest,
    note: str,
) -> dict[str, Any]:
    reason = (note or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection note is required")

    res = await db.execute(
        select(StudentSchoolInterest).where(
            StudentSchoolInterest.id == interest_id,
            StudentSchoolInterest.school_id == school_id,
        )
    )
    interest = res.scalar_one_or_none()
    if not interest:
        raise HTTPException(status_code=404, detail="School interest not found")
    if interest.status != "pending_principal":
        raise HTTPException(status_code=400, detail=f"Interest is already {interest.status}")

    interest.status = "rejected"
    interest.principal_note = reason
    interest.reviewed_by = principal.id
    interest.reviewed_at = _utcnow()
    interest.updated_at = _utcnow()
    await db.commit()
    return {"status": "rejected"}


def _step(status: str, *, done: bool, detail: str = "") -> dict[str, Any]:
    return {"status": status, "done": done, "detail": detail}


async def build_onboarding_timeline(db: AsyncSession, student: SignupRequest) -> dict[str, Any]:
    if (student.onboarding_version or "v1") != ONBOARDING_V2:
        return {"onboarding_version": "v1", "legacy": True, "unlocked": True}

    link_res = await db.execute(
        select(StudentFamilyLink).where(StudentFamilyLink.student_signup_id == student.id)
    )
    link = link_res.scalar_one_or_none()
    parent_kyc = KycStatus.pending
    if link:
        p_res = await db.execute(select(SignupRequest).where(SignupRequest.id == link.parent_signup_id))
        parent = p_res.scalar_one_or_none()
        if parent:
            parent_kyc = parent.kyc_status

    interest_res = await db.execute(
        select(StudentSchoolInterest).where(StudentSchoolInterest.student_signup_id == student.id)
    )
    interest = interest_res.scalar_one_or_none()
    school_student = await resolve_school_student(db, student)

    accepted_circle = await db.execute(
        select(StudentCircleInterestRequest).where(
            StudentCircleInterestRequest.student_signup_id == student.id,
            StudentCircleInterestRequest.status == "accepted",
        )
    )
    accepted = accepted_circle.scalar_one_or_none()

    student_kyc_done = student.kyc_status == KycStatus.approved
    school_done = interest and interest.status == "approved" and school_student is not None
    parent_done = parent_kyc == KycStatus.approved
    circle_done = accepted is not None

    steps = [
        _step(
            "zenk_kyc",
            done=student_kyc_done,
            detail="ZenK reviews your documents" if not student_kyc_done else "Approved",
        ),
        _step(
            "school_interest",
            done=bool(interest),
            detail=(
                f"Waiting for principal at selected school"
                if interest and interest.status == "pending_principal"
                else "School interest submitted"
                if interest
                else "Select school at signup"
            ),
        ),
        _step(
            "school_admitted",
            done=school_done,
            detail=(
                "Principal admitted you"
                if school_done
                else interest.principal_note
                if interest and interest.status == "rejected"
                else "Awaiting principal approval"
            ),
        ),
        _step(
            "parent_kyc",
            done=parent_done,
            detail="Parent/guardian KYC approved" if parent_done else "Submitted at signup — awaiting ZenK approval",
        ),
        _step(
            "circle_joined",
            done=circle_done,
            detail="In a sponsorship circle" if circle_done else "Request an open circle after school admission",
        ),
    ]

    unlocked_dashboard = school_done and student_kyc_done and parent_done
    unlocked_circle_request = unlocked_dashboard and not circle_done

    return {
        "onboarding_version": ONBOARDING_V2,
        "legacy": False,
        "steps": steps,
        "unlocked_dashboard": unlocked_dashboard,
        "unlocked_circle_request": unlocked_circle_request,
        "in_circle": circle_done,
        "school_interest_status": interest.status if interest else None,
    }


async def _circle_has_student(db: AsyncSession, circle_id: str) -> bool:
    cnt_res = await db.execute(
        select(func.count())
        .select_from(SchoolStudent)
        .where(SchoolStudent.circle_id == circle_id)
    )
    if int(cnt_res.scalar() or 0) > 0:
        return True
    acc_res = await db.execute(
        select(func.count())
        .select_from(StudentCircleInterestRequest)
        .where(
            StudentCircleInterestRequest.circle_id == circle_id,
            StudentCircleInterestRequest.status == "accepted",
        )
    )
    return int(acc_res.scalar() or 0) > 0


async def list_student_circle_interests(
    db: AsyncSession,
    student: SignupRequest,
) -> list[dict[str, Any]]:
    res = await db.execute(
        select(StudentCircleInterestRequest, SponsorCircle)
        .join(SponsorCircle, SponsorCircle.id == StudentCircleInterestRequest.circle_id)
        .where(StudentCircleInterestRequest.student_signup_id == student.id)
        .order_by(StudentCircleInterestRequest.created_at.desc())
    )
    rows = []
    for req, circle in res.all():
        rows.append({
            "id": req.id,
            "circle_id": req.circle_id,
            "circle_name": circle.name,
            "help_comment": req.help_comment,
            "status": req.status,
            "pseudonym": req.pseudonym,
            "probe_expires_at": req.probe_expires_at.isoformat() if req.probe_expires_at else None,
            "leader_note": req.leader_note,
            "created_at": req.created_at.isoformat() if req.created_at else None,
        })
    return rows


async def list_open_circles_for_students(db: AsyncSession) -> list[dict[str, str]]:
    res = await db.execute(select(SponsorCircle).order_by(SponsorCircle.name))
    out = []
    for circle in res.scalars().all():
        if not await _circle_has_student(db, circle.id):
            out.append({"id": circle.id, "name": circle.name, "description": circle.description or ""})
    return out


async def _student_already_in_circle(db: AsyncSession, student_signup_id: str) -> bool:
    res = await db.execute(
        select(StudentCircleInterestRequest).where(
            StudentCircleInterestRequest.student_signup_id == student_signup_id,
            StudentCircleInterestRequest.status == "accepted",
        )
    )
    return res.scalar_one_or_none() is not None


async def submit_circle_interest(
    db: AsyncSession,
    student: SignupRequest,
    *,
    circle_id: str,
    help_comment: str,
) -> dict[str, Any]:
    timeline = await build_onboarding_timeline(db, student)
    if not timeline.get("unlocked_circle_request"):
        raise HTTPException(
            status_code=403,
            detail="Complete ZenK KYC, school admission, and parent KYC before requesting a circle.",
        )
    if await _student_already_in_circle(db, student.id):
        raise HTTPException(status_code=400, detail="You are already in a sponsorship circle")

    if await _circle_has_student(db, circle_id):
        raise HTTPException(status_code=400, detail="This circle already has a student beneficiary")

    comment = (help_comment or "").strip()
    if len(comment) < 10:
        raise HTTPException(status_code=400, detail="Please share why you need support (at least 10 characters)")

    dup = await db.execute(
        select(StudentCircleInterestRequest).where(
            StudentCircleInterestRequest.student_signup_id == student.id,
            StudentCircleInterestRequest.circle_id == circle_id,
            StudentCircleInterestRequest.status.in_(("pending_leader", "probing")),
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You already have a pending request to this circle")

    persona = await get_or_create_persona(student, db)
    expires = _utcnow() + timedelta(days=PROBE_DAYS)

    row = StudentCircleInterestRequest(
        student_signup_id=student.id,
        circle_id=circle_id,
        help_comment=comment,
        status="pending_leader",
        pseudonym=persona.nickname,
        probe_expires_at=expires,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "id": row.id,
        "circle_id": circle_id,
        "pseudonym": row.pseudonym,
        "probe_expires_at": expires.isoformat(),
        "status": row.status,
    }


async def _brief_academic_for_leader(
    db: AsyncSession,
    student: SignupRequest,
    school_student: Optional[SchoolStudent],
) -> dict[str, Any]:
    grade = student.grade_or_year or (school_student.grade if school_student else None)
    attendance = int(school_student.attendance_pct or 0) if school_student else None
    approved_grades = []
    sub_res = await db.execute(
        select(ParentAcademicSubmission)
        .where(
            ParentAcademicSubmission.student_signup_id == student.id,
            ParentAcademicSubmission.status == "approved",
        )
        .order_by(ParentAcademicSubmission.created_at.desc())
        .limit(3)
    )
    from app.services.parent_portal import submission_brief_dict

    for sub in sub_res.scalars().all():
        approved_grades.append(submission_brief_dict(sub))
    return {
        "grade": grade,
        "attendance_pct": attendance,
        "guardian_uploads_approved": approved_grades,
        "zqa_score": None,
        "note": "ZQA available after school quarterly reports",
    }


async def list_leader_circle_interests(
    db: AsyncSession,
    leader: SignupRequest,
    circle_id: str,
    *,
    status: str = "pending_leader",
) -> list[dict[str, Any]]:
    mem_res = await db.execute(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == leader.id,
            CircleMember.role.in_(("lead", "sponsor_leader", "sponsor")),
        )
    )
    if not mem_res.scalar_one_or_none() and leader.persona != Persona.sponsor_leader:
        raise HTTPException(status_code=403, detail="Not a leader of this circle")

    q = select(StudentCircleInterestRequest).where(
        StudentCircleInterestRequest.circle_id == circle_id
    )
    if status != "all":
        q = q.where(StudentCircleInterestRequest.status == status)
    q = q.order_by(StudentCircleInterestRequest.created_at.desc())
    res = await db.execute(q)

    rows = []
    for req in res.scalars().all():
        stu_res = await db.execute(select(SignupRequest).where(SignupRequest.id == req.student_signup_id))
        student = stu_res.scalar_one_or_none()
        school_student = await resolve_school_student(db, student) if student else None
        rows.append({
            "id": req.id,
            "pseudonym": req.pseudonym,
            "help_comment": req.help_comment,
            "status": req.status,
            "probe_expires_at": req.probe_expires_at.isoformat() if req.probe_expires_at else None,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "brief": await _brief_academic_for_leader(db, student, school_student) if student else {},
        })
    return rows


async def leader_decide_circle_interest(
    db: AsyncSession,
    *,
    request_id: str,
    leader: SignupRequest,
    action: str,
    note: Optional[str] = None,
) -> dict[str, Any]:
    res = await db.execute(
        select(StudentCircleInterestRequest).where(StudentCircleInterestRequest.id == request_id)
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status not in ("pending_leader", "probing"):
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    mem_res = await db.execute(
        select(CircleMember).where(
            CircleMember.circle_id == req.circle_id,
            CircleMember.user_id == leader.id,
            CircleMember.role.in_(("lead", "sponsor_leader", "sponsor")),
        )
    )
    if not mem_res.scalar_one_or_none() and leader.persona != Persona.sponsor_leader:
        raise HTTPException(status_code=403, detail="Not a leader of this circle")

    if action == "reject":
        req.status = "rejected"
        req.leader_signup_id = leader.id
        req.leader_note = (note or "").strip() or "Not selected at this time"
        req.reviewed_at = _utcnow()
        req.updated_at = _utcnow()
        await db.commit()
        return {"status": "rejected"}

    if action != "accept":
        raise HTTPException(status_code=400, detail="action must be accept or reject")

    if await _circle_has_student(db, req.circle_id):
        raise HTTPException(status_code=409, detail="Circle already has a student")

    stu_res = await db.execute(select(SignupRequest).where(SignupRequest.id == req.student_signup_id))
    student = stu_res.scalar_one_or_none()
    school_student = await resolve_school_student(db, student) if student else None
    if not school_student:
        raise HTTPException(status_code=400, detail="Student must be school-admitted first")

    c_res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == req.circle_id))
    circle = c_res.scalar_one_or_none()

    from app.services.school_circle_sync import sync_school_student_circle_link

    await sync_school_student_circle_link(
        db,
        school_student,
        req.circle_id,
        leader=leader,
        force_sl=True,
    )

    if student:
        persona = await get_or_create_persona(student, db)
        if req.pseudonym != persona.nickname:
            req.pseudonym = persona.nickname

    req.status = "accepted"
    req.leader_signup_id = leader.id
    req.leader_note = (note or "").strip() or None
    req.reviewed_at = _utcnow()
    req.updated_at = _utcnow()

    other_res = await db.execute(
        select(StudentCircleInterestRequest).where(
            StudentCircleInterestRequest.student_signup_id == req.student_signup_id,
            StudentCircleInterestRequest.id != req.id,
            StudentCircleInterestRequest.status.in_(("pending_leader", "probing")),
        )
    )
    for other in other_res.scalars().all():
        other.status = "withdrawn"
        other.updated_at = _utcnow()

    existing_mem = await db.execute(
        select(CircleMember).where(
            CircleMember.circle_id == req.circle_id,
            CircleMember.user_id == req.student_signup_id,
        )
    )
    if not existing_mem.scalar_one_or_none():
        db.add(CircleMember(circle_id=req.circle_id, user_id=req.student_signup_id, role="student"))

    link_res = await db.execute(
        select(StudentFamilyLink).where(StudentFamilyLink.student_signup_id == req.student_signup_id)
    )
    link = link_res.scalar_one_or_none()
    if link:
        link.circle_id = req.circle_id
        link.updated_at = _utcnow()

    await provision_parent_after_student_enrollment(db, school_student=school_student, circle_id=req.circle_id)
    await db.commit()
    return {"status": "accepted", "circle_id": req.circle_id}


async def post_probe_message(
    db: AsyncSession,
    *,
    request_id: str,
    sender: SignupRequest,
    body: str,
    sender_role: str,
) -> dict[str, Any]:
    res = await db.execute(
        select(StudentCircleInterestRequest).where(StudentCircleInterestRequest.id == request_id)
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status in ("rejected", "withdrawn", "accepted"):
        raise HTTPException(status_code=400, detail="Probe chat is closed for this request")
    if req.probe_expires_at and _utcnow() > req.probe_expires_at:
        raise HTTPException(status_code=400, detail="Probe chat window has expired (7 days)")

    text = (body or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if sender_role == "student" and sender.id != req.student_signup_id:
        raise HTTPException(status_code=403, detail="Not your request")
    if sender_role == "leader":
        mem_res = await db.execute(
            select(CircleMember).where(
                CircleMember.circle_id == req.circle_id,
                CircleMember.user_id == sender.id,
            )
        )
        if not mem_res.scalar_one_or_none() and sender.persona != Persona.sponsor_leader:
            raise HTTPException(status_code=403, detail="Not a leader of this circle")

    if req.status == "pending_leader":
        req.status = "probing"
        req.updated_at = _utcnow()

    msg = StudentProbeMessage(
        interest_request_id=request_id,
        sender_role=sender_role,
        sender_signup_id=sender.id,
        body=text,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return {
        "id": msg.id,
        "sender_role": msg.sender_role,
        "body": msg.body,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


async def list_probe_messages(db: AsyncSession, request_id: str, user: SignupRequest) -> list[dict[str, Any]]:
    res = await db.execute(
        select(StudentCircleInterestRequest).where(StudentCircleInterestRequest.id == request_id)
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    allowed = user.id == req.student_signup_id
    if not allowed:
        mem_res = await db.execute(
            select(CircleMember).where(
                CircleMember.circle_id == req.circle_id,
                CircleMember.user_id == user.id,
            )
        )
        allowed = mem_res.scalar_one_or_none() is not None or user.persona == Persona.sponsor_leader
    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied")

    msg_res = await db.execute(
        select(StudentProbeMessage)
        .where(StudentProbeMessage.interest_request_id == request_id)
        .order_by(StudentProbeMessage.created_at.asc())
    )
    return [
        {
            "id": m.id,
            "sender_role": m.sender_role,
            "body": m.body,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msg_res.scalars().all()
    ]
