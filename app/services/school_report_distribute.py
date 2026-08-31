"""Live academic report distribution: PDF + Gmail to circle + parent + mentor."""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember
from app.core.settings import settings
from app.models.school import SchoolFaculty, SchoolProfile, SchoolReport, SchoolStudent, SchoolStudentNarrative
from app.models.signup import SignupRequest
from app.models.student_family import StudentFamilyLink
from app.services.circle_school_partner import ensure_student_circle_id
from app.services.email import email_delivery_ready, send_email
from app.services.email_templates import render_school_report_distributed_html
from app.services.school_circle_sync import LEADER_ROLES
from app.services.school_transcript import build_student_transcript
from app.services.school_transcript_pdf import generate_transcript_pdf, transcript_pdf_filename

logger = logging.getLogger(__name__)


def _role_label(role: str) -> str:
    r = (role or "").lower()
    if r in LEADER_ROLES or r in {"lead", "coordinator", "sponsor_leader", "sponsor"}:
        if r in {"sponsor_leader", "lead", "coordinator"}:
            return "leader"
        return "member"
    if r == "mentor":
        return "mentor"
    return "member"


async def resolve_distribution_recipients(
    db: AsyncSession,
    *,
    student: SchoolStudent,
) -> list[dict[str, str]]:
    """
    Resolve unique email recipients for distribution:
    - Circle leaders + members (signup emails)
    - Assigned mentor (faculty email)
    - Linked parent/guardian (family link)
    """
    recipients: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(email: Optional[str], name: str, role: str, user_id: Optional[str] = None) -> None:
        addr = (email or "").strip()
        if not addr or "@" not in addr:
            return
        key = addr.lower()
        if key in seen:
            return
        seen.add(key)
        recipients.append(
            {
                "email": addr,
                "name": (name or "").strip() or addr,
                "role": role,
                "user_id": user_id or "",
            }
        )

    circle_id = await ensure_student_circle_id(db, student)
    if circle_id:
        rows = await db.execute(
            select(CircleMember, SignupRequest)
            .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
            .where(CircleMember.circle_id == circle_id)
            .order_by(CircleMember.joined_at.asc())
        )
        for cm, signup in rows.all():
            role = _role_label(cm.role or "")
            # Prefer leader label when role matches
            if (cm.role or "").lower() in {"sponsor_leader", "lead", "coordinator"}:
                role = "leader"
            _add(signup.email, signup.full_name or "", role, signup.id)

    if student.mentor_faculty_id:
        fac = await db.execute(
            select(SchoolFaculty).where(SchoolFaculty.id == student.mentor_faculty_id)
        )
        mentor = fac.scalar_one_or_none()
        if mentor:
            _add(mentor.email, mentor.display_name or student.mentor_name or "Mentor", "mentor")

    # Parent / guardian via family link (signup_request_id on school student)
    parent_signup: Optional[SignupRequest] = None
    if student.signup_request_id:
        link_res = await db.execute(
            select(StudentFamilyLink)
            .where(StudentFamilyLink.student_signup_id == student.signup_request_id)
            .limit(1)
        )
        link = link_res.scalar_one_or_none()
        if link:
            p_res = await db.execute(
                select(SignupRequest).where(SignupRequest.id == link.parent_signup_id)
            )
            parent_signup = p_res.scalar_one_or_none()
    if parent_signup is None:
        # Fallback: school_student_id on family links
        link_res = await db.execute(
            select(StudentFamilyLink).where(StudentFamilyLink.school_student_id == student.id).limit(1)
        )
        link = link_res.scalar_one_or_none()
        if link:
            p_res = await db.execute(
                select(SignupRequest).where(SignupRequest.id == link.parent_signup_id)
            )
            parent_signup = p_res.scalar_one_or_none()
    if parent_signup:
        _add(parent_signup.email, parent_signup.full_name or "Parent", "parent", parent_signup.id)

    return recipients


async def distribute_student_report_live(
    db: AsyncSession,
    *,
    profile: SchoolProfile,
    student: SchoolStudent,
    actor: SignupRequest,
    also_notify_circle_chat: bool = True,
) -> dict[str, Any]:
    """
    Build the same transcript as preview, attach PDF, email recipients via Gmail/SMTP/Resend,
    optionally post circle chat briefing, and mark report rows as Distributed.
    """
    if not email_delivery_ready():
        return {
            "status": "error",
            "message": (
                "Email is not configured. Enable SMTP (Gmail app password) or set RESEND_API_KEY."
            ),
            "emails_sent": 0,
            "recipients": [],
        }

    transcript = await build_student_transcript(db, profile=profile, student=student)
    pdf_bytes = generate_transcript_pdf(transcript)
    filename = transcript_pdf_filename(transcript)

    recipients = await resolve_distribution_recipients(db, student=student)
    if not recipients:
        return {
            "status": "error",
            "message": (
                f"No email recipients found for {student.full_name}. "
                "Link a sponsor circle (leaders/members), parent family account, or mentor email."
            ),
            "emails_sent": 0,
            "recipients": [],
            "circle_id": student.circle_id,
            "circle_name": student.circle_name,
        }

    website = getattr(settings, "website_url", None) or "https://in.zenkimpact.com"
    student_name = student.full_name
    school_name = profile.school_name
    fy = transcript.get("fy") or profile.fy_current or "2025-26"
    quarter = (transcript.get("narrative") or {}).get("quarter") or "Q4"

    sent: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []

    for rec in recipients:
        role = rec["role"]
        role_title = {
            "leader": "Sponsor Circle Leader",
            "member": "Circle Member",
            "mentor": "Mentor",
            "parent": "Parent / Guardian",
        }.get(role, "Partner")

        subject = f"ZenK progress transcript — {student_name} · {quarter} · {school_name}"
        text_body = (
            f"Hello {rec['name']},\n\n"
            f"{school_name} has distributed the official ZenK progress transcript for {student_name} "
            f"({quarter}, FY {fy}).\n\n"
            f"You are receiving this as: {role_title}.\n"
            f"The PDF report card is attached — it matches the school dashboard preview.\n\n"
            f"— ZenK Impact\n"
        )
        html_body = render_school_report_distributed_html(
            recipient_name=rec["name"],
            role_title=role_title,
            student_name=student_name,
            school_name=school_name,
            quarter=quarter,
            fy=fy,
            circle_name=student.circle_name or "Sponsor circle",
            website_url=website,
        )
        try:
            await send_email(
                subject=subject,
                to_email=rec["email"],
                text_body=text_body,
                html_body=html_body,
                attachments=[(filename, pdf_bytes, "application/pdf")],
                send_individually=True,
            )
            sent.append(rec)
        except Exception as exc:
            logger.exception("Report distribute email failed to=%s", rec["email"])
            failed.append({**rec, "error": str(exc)[:200]})

    chat_result: dict[str, Any] = {}
    if also_notify_circle_chat:
        try:
            from app.services.kia_event_briefings import emit_report_published

            narr = transcript.get("narrative") or {}
            chat_result = await emit_report_published(
                db,
                school_id=profile.id,
                student=student,
                quarter=quarter,
                fy=fy,
                teacher_name=narr.get("teacher_name")
                or actor.full_name
                or profile.principal_name
                or "School",
                narrative=narr.get("narrative"),
                finalized=True,
            ) or {}
            chat_result["distributed"] = bool(
                chat_result.get("circle_chat") or chat_result.get("partner_thread")
            )
        except Exception:
            logger.exception("Circle chat notify failed during distribute for %s", student.id)
            chat_result = {"distributed": False}

    # Persist distribution on report rows + student status
    reports_res = await db.execute(
        select(SchoolReport).where(
            SchoolReport.school_id == profile.id,
            SchoolReport.student_id == student.id,
        )
    )
    for row in reports_res.scalars().all():
        row.status = "Distributed"

    if student.q_report_status in (None, "", "Pending", "Submitted"):
        student.q_report_status = "Finalized"

    # Ensure latest narrative marked finalized when we distribute
    narr_res = await db.execute(
        select(SchoolStudentNarrative).where(SchoolStudentNarrative.student_id == student.id)
    )
    for n in narr_res.scalars().all():
        n.finalized = True

    leaders = [r for r in sent if r["role"] == "leader"]
    members = [r for r in sent if r["role"] == "member"]
    parents = [r for r in sent if r["role"] == "parent"]
    mentors = [r for r in sent if r["role"] == "mentor"]

    if not sent and failed:
        return {
            "status": "error",
            "message": f"Could not send emails for {student_name}. Check SMTP/Gmail settings and try again.",
            "emails_sent": 0,
            "recipients": recipients,
            "failed": failed,
            "circle_chat": chat_result,
        }

    parts = [f"Emailed PDF report card for {student_name}"]
    detail_bits = []
    if leaders:
        detail_bits.append(f"{len(leaders)} leader(s)")
    if members:
        detail_bits.append(f"{len(members)} member(s)")
    if parents:
        detail_bits.append(f"{len(parents)} parent(s)")
    if mentors:
        detail_bits.append(f"{len(mentors)} mentor(s)")
    if detail_bits:
        parts.append("to " + ", ".join(detail_bits))
    if failed:
        parts.append(f"({len(failed)} failed)")
    if chat_result.get("distributed"):
        parts.append("+ posted to circle chat")

    return {
        "status": "success",
        "message": ". ".join(parts) + ".",
        "emails_sent": len(sent),
        "recipients": [{"email": r["email"], "name": r["name"], "role": r["role"]} for r in sent],
        "failed": failed,
        "filename": filename,
        "circle_id": student.circle_id or chat_result.get("circle_id"),
        "circle_name": student.circle_name or chat_result.get("circle_name"),
        "circle_chat": bool(chat_result.get("circle_chat") or chat_result.get("partner_thread")),
    }
