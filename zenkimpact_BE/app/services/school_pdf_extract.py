"""Extract quarterly report fields from uploaded PDFs via LLM."""

from __future__ import annotations

import io
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import SchoolFormSubmission, SchoolStudent
from app.models.signup import SignupRequest
from app.services.kia import _call_llm
from app.services.school_reports import apply_quarterly_report
from app.services.school_report_validate import validate_quarterly_payload

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM = """You extract structured quarterly school report data from document text.
Return ONLY valid JSON matching the schema. Use numbers not strings for numeric fields.
If a field is missing in the document, use null for optional fields or reasonable defaults:
risk_level "Low", ready_for_zenk true, fy "2025-26", quarter "Q4".
Match student_name to the school's enrolled students list when possible."""

EXTRACT_SCHEMA_HINT = """
{
  "student_id": "uuid or null",
  "student_name": "string",
  "quarter": "Q1|Q2|Q3|Q4",
  "fy": "2025-26",
  "attendance_pct": 0-100,
  "avg_score": 0-100,
  "risk_level": "Low|Medium|High",
  "rank_in_class": "string or null",
  "class_size": integer or null,
  "circle_name": "string or null",
  "subject_scores": {"maths":0,"science":0,"english":0,"social":0,"hindi":0,"sanskrit":null},
  "blooms": {"remember":0,"understand":0,"apply":0,"analyse":0,"evaluate":0,"create":0},
  "sel": {"self_awareness":0,"self_management":0,"social_awareness":0,"relationship_skills":0,"responsible_decisions":0},
  "narrative": "string",
  "tutor_recommendation": "string or null",
  "ready_for_zenk": true,
  "confidence": "high|medium|low",
  "notes": "brief extraction caveats"
}
"""


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ValueError("PDF support not installed on server") from e

    reader = PdfReader(io.BytesIO(file_bytes))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    text = "\n".join(parts).strip()
    if len(text) < 40:
        raise ValueError(
            "Could not read enough text from this PDF. "
            "Use a text-based PDF (not a scanned image), or enter data via the form/CSV."
        )
    return text[:12000]


async def llm_extract_report_fields(
    document_text: str,
    students: list[SchoolStudent],
    *,
    hint_student_id: Optional[str] = None,
    hint_quarter: Optional[str] = None,
) -> dict[str, Any]:
    roster = [
        {"id": s.id, "full_name": s.full_name, "grade": s.grade}
        for s in students
    ]
    user_msg = (
        f"Enrolled students: {json.dumps(roster)}\n"
        f"Upload hints: student_id={hint_student_id or 'none'}, quarter={hint_quarter or 'none'}\n\n"
        f"DOCUMENT TEXT:\n{document_text}\n\n"
        f"Return JSON only:\n{EXTRACT_SCHEMA_HINT}"
    )
    raw = await _call_llm(
        system_prompt=EXTRACT_SYSTEM,
        user_message=user_msg,
        max_tokens=2048,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    if not raw:
        raise ValueError("AI extraction unavailable. Try again or use the web form.")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("PDF extract invalid JSON: %s", raw[:500])
        raise ValueError("AI returned invalid data. Please use CSV or the web form.") from e

    return data


def _resolve_student_id(
    extracted: dict[str, Any],
    students: list[SchoolStudent],
    hint_student_id: Optional[str],
) -> str:
    if hint_student_id:
        match = next((s for s in students if s.id == hint_student_id), None)
        if match:
            return match.id

    eid = extracted.get("student_id")
    if eid:
        match = next((s for s in students if s.id == eid), None)
        if match:
            return match.id

    name = (extracted.get("student_name") or "").strip().lower()
    if name:
        match = next((s for s in students if s.full_name.strip().lower() == name), None)
        if match:
            return match.id

    if len(students) == 1:
        return students[0].id

    raise ValueError(
        "Could not match student. Select a student when uploading or include student_id in the PDF."
    )


def normalized_payload(extracted: dict[str, Any], quarter_hint: Optional[str]) -> dict[str, Any]:
    quarter = (extracted.get("quarter") or quarter_hint or "Q4").upper()
    if quarter not in ("Q1", "Q2", "Q3", "Q4"):
        quarter = "Q4"

    risk = extracted.get("risk_level") or "Low"
    if risk not in ("Low", "Medium", "High"):
        risk = "Low"

    subj = extracted.get("subject_scores") or {}
    blooms = extracted.get("blooms") or {}
    sel = extracted.get("sel") or {}

    return {
        "quarter": quarter,
        "fy": extracted.get("fy") or "2025-26",
        "attendance_pct": float(extracted.get("attendance_pct") or 0),
        "avg_score": float(extracted.get("avg_score") or 0),
        "risk_level": risk,
        "rank_in_class": extracted.get("rank_in_class"),
        "class_size": extracted.get("class_size"),
        "circle_name": extracted.get("circle_name"),
        "subject_scores": {
            "maths": float(subj.get("maths") or 0),
            "science": float(subj.get("science") or 0),
            "english": float(subj.get("english") or 0),
            "social": float(subj.get("social") or 0),
            "hindi": float(subj.get("hindi") or 0),
            "sanskrit": float(subj["sanskrit"]) if subj.get("sanskrit") not in (None, "") else None,
        },
        "blooms": {k: float(blooms.get(k) or 0) for k in (
            "remember", "understand", "apply", "analyse", "evaluate", "create"
        )},
        "sel": {k: float(sel.get(k) or 0) for k in (
            "self_awareness", "self_management", "social_awareness",
            "relationship_skills", "responsible_decisions",
        )},
        "narrative": (extracted.get("narrative") or "").strip(),
        "tutor_recommendation": extracted.get("tutor_recommendation"),
        "ready_for_zenk": bool(extracted.get("ready_for_zenk", True)),
    }


async def create_pdf_review_submission(
    db: AsyncSession,
    *,
    school_id: str,
    user: SignupRequest,
    student_id: str,
    filename: str,
    extracted: dict[str, Any],
    payload: dict[str, Any],
    raw_text_preview: str,
) -> SchoolFormSubmission:
    submission = SchoolFormSubmission(
        id=str(uuid.uuid4()),
        school_id=school_id,
        student_id=student_id,
        quarter=payload["quarter"],
        fy=payload.get("fy") or "2025-26",
        source="pdf",
        submitted_by_user_id=user.id,
        submitted_by_name=user.full_name or "School staff",
        submitted_by_email=user.email or "",
        submitted_at=datetime.utcnow(),
        status="pending_review",
        payload={
            "extracted": extracted,
            "draft": payload,
            "filename": filename,
            "raw_text_preview": raw_text_preview[:2000],
        },
    )
    db.add(submission)
    await db.flush()
    return submission


async def process_pdf_upload(
    db: AsyncSession,
    *,
    school_id: str,
    user: SignupRequest,
    file_bytes: bytes,
    filename: str,
    student_id: Optional[str] = None,
    quarter: Optional[str] = None,
) -> dict[str, Any]:
    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == school_id)
    )
    students = students_res.scalars().all()
    if not students:
        raise ValueError("No students enrolled. Add a student before uploading reports.")

    text = extract_text_from_pdf(file_bytes)
    extracted = await llm_extract_report_fields(
        text, students, hint_student_id=student_id, hint_quarter=quarter
    )
    resolved_id = _resolve_student_id(extracted, students, student_id)
    payload = normalized_payload(extracted, quarter)

    if not payload["narrative"]:
        payload["narrative"] = "See uploaded PDF — please edit narrative before approving."

    submission = await create_pdf_review_submission(
        db,
        school_id=school_id,
        user=user,
        student_id=resolved_id,
        filename=filename,
        extracted=extracted,
        payload=payload,
        raw_text_preview=text,
    )
    await db.commit()

    student = next(s for s in students if s.id == resolved_id)
    return {
        "status": "pending_review",
        "message": f"Extracted report for {student.full_name}. Review and approve to save live data.",
        "review_id": submission.id,
        "student_id": resolved_id,
        "student_name": student.full_name,
        "quarter": payload["quarter"],
        "confidence": extracted.get("confidence", "medium"),
        "notes": extracted.get("notes"),
        "draft": payload,
    }


async def approve_pdf_review(
    db: AsyncSession,
    *,
    school_id: str,
    user: SignupRequest,
    review_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    res = await db.execute(
        select(SchoolFormSubmission).where(
            SchoolFormSubmission.id == review_id,
            SchoolFormSubmission.school_id == school_id,
            SchoolFormSubmission.status == "pending_review",
        )
    )
    review = res.scalar_one_or_none()
    if not review:
        raise ValueError("Review not found or already processed.")

    sid = payload.get("student_id") or review.student_id
    stu_res = await db.execute(
        select(SchoolStudent).where(
            SchoolStudent.id == sid,
            SchoolStudent.school_id == school_id,
        )
    )
    student = stu_res.scalar_one_or_none()
    if not student:
        raise ValueError("Student not found.")

    payload = {**payload, "student_id": student.id}
    payload["quarter"] = (payload.get("quarter") or review.quarter).upper()
    validate_quarterly_payload(payload)

    submission = await apply_quarterly_report(
        db,
        school_id=school_id,
        student=student,
        user=user,
        payload=payload,
        source="pdf",
    )
    review.status = "approved"
    review.payload = {**(review.payload or {}), "approved_submission_id": submission.id}
    await db.commit()

    return {
        "status": "success",
        "message": f"Approved and saved live data for {student.full_name} ({payload['quarter']}).",
        "submission_id": submission.id,
        "review_id": review_id,
    }
