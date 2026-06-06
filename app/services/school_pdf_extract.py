"""Extract quarterly report fields from uploaded PDFs via LLM."""

from __future__ import annotations

import io
import json
import logging
import re
import uuid
from datetime import datetime
from statistics import mean
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
Return ONLY valid JSON. Use numbers (not strings) for numeric fields.

CRITICAL RULES:
- NEVER use 0 for a missing field. Use null when a value is not stated in the document.
- For simple "Student Marks Report" PDFs with only a subject/marks table:
  - Map Mathematics/Math → subject_scores.maths
  - Map Physics, Chemistry, Biology, Computer Science → average into subject_scores.science (one number)
  - Map English → subject_scores.english
  - Map Social Studies/History/Geography → subject_scores.social
  - Map Hindi → subject_scores.hindi
  - Map Sanskrit → subject_scores.sanskrit
  - Leave attendance_pct null if attendance is not mentioned
  - Set blooms and sel to null (not zero) if Bloom's/SEL are not in the document
  - Put "Overall Performance: …" or teacher comments in narrative
  - Compute avg_score as the mean of all subject marks present, or null if none
- Match student_name to the enrolled students list when possible.
- Defaults only when needed: risk_level "Low", ready_for_zenk true, fy "2025-26", quarter "Q4"."""

EXTRACT_SCHEMA_HINT = """
{
  "student_id": "uuid or null",
  "student_name": "string or null",
  "quarter": "Q1|Q2|Q3|Q4",
  "fy": "2025-26",
  "attendance_pct": null,
  "avg_score": null,
  "risk_level": "Low|Medium|High",
  "rank_in_class": "string or null",
  "class_size": null,
  "circle_name": "string or null",
  "subject_scores": {"maths": null, "science": null, "english": null, "social": null, "hindi": null, "sanskrit": null},
  "blooms": null,
  "sel": null,
  "narrative": "string",
  "tutor_recommendation": "string or null",
  "ready_for_zenk": true,
  "confidence": "high|medium|low",
  "notes": "brief extraction caveats",
  "extra_subjects": [{"name": "Computer Science", "score": 96}]
}
"""

_SUBJECT_BUCKETS: dict[str, tuple[str, ...]] = {
    "maths": ("mathematics", "maths", "math"),
    "science": (
        "physics", "chemistry", "biology", "science", "computer science",
        "computer", "cs", "ipc", "general science", "biotechnology",
    ),
    "english": ("english", "eng"),
    "social": ("social", "social science", "sst", "history", "geography", "civics", "economics"),
    "hindi": ("hindi",),
    "sanskrit": ("sanskrit",),
}


def _norm_subject(label: str) -> str:
    return re.sub(r"\s+", " ", (label or "").strip().lower())


def _bucket_for_subject(label: str) -> Optional[str]:
    n = _norm_subject(label)
    if not n or n in ("subject", "marks", "total", "grand total"):
        return None
    for bucket, aliases in _SUBJECT_BUCKETS.items():
        if n in aliases or any(n.startswith(a + " ") or n.endswith(" " + a) for a in aliases):
            return bucket
        if any(a in n for a in aliases if len(a) > 4):
            return bucket
    return None


def _parse_score_token(token: str) -> Optional[float]:
    try:
        val = float(str(token).strip().replace("%", ""))
    except (TypeError, ValueError):
        return None
    if val < 0 or val > 100:
        return None
    return round(val, 2)


def _parse_subject_mark_line(line: str) -> Optional[tuple[str, float]]:
    line = line.strip()
    if not line:
        return None
    parts = [p.strip() for p in re.split(r"\||\t", line) if p.strip()]
    if len(parts) >= 2 and _parse_score_token(parts[-1]) is not None:
        return parts[0], _parse_score_token(parts[-1])
    m = re.match(r"^(.+?)\s+(\d{1,3}(?:\.\d+)?)\s*$", line)
    if m and _parse_score_token(m.group(2)) is not None:
        return m.group(1).strip(), _parse_score_token(m.group(2))
    return None


def parse_marks_report_heuristics(document_text: str) -> Optional[dict[str, Any]]:
    """Parse simple name + subject/marks table PDFs without inventing zeros."""
    text = document_text.strip()
    if len(text) < 20:
        return None
    lower = text.lower()
    if "marks" not in lower and "subject" not in lower:
        return None

    bucket_scores: dict[str, list[float]] = {k: [] for k in _SUBJECT_BUCKETS}
    extra_subjects: list[dict[str, Any]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or re.match(r"^subject\s+marks", line, re.I):
            continue
        parsed = _parse_subject_mark_line(line)
        if not parsed:
            continue
        subj_label, score = parsed
        bucket = _bucket_for_subject(subj_label)
        if bucket:
            bucket_scores[bucket].append(score)
        else:
            extra_subjects.append({"name": subj_label, "score": score})

    has_marks = any(bucket_scores[k] for k in bucket_scores) or extra_subjects
    if not has_marks:
        return None

    subject_scores: dict[str, Optional[float]] = {
        k: round(mean(v), 2) if v else None for k, v in bucket_scores.items()
    }

    name_m = re.search(r"(?:^|\n)\s*name\s*[:\-]\s*(.+)", text, re.I)
    student_name = name_m.group(1).strip() if name_m else None

    perf_m = re.search(r"overall\s+performance\s*[:\-]\s*(.+)", text, re.I)
    narrative = perf_m.group(1).strip() if perf_m else None
    if narrative:
        narrative = f"Overall Performance: {narrative}"

    all_scores = [s for scores in bucket_scores.values() for s in scores]
    all_scores.extend(x["score"] for x in extra_subjects)
    avg_score = round(mean(all_scores), 2) if all_scores else None

    notes_parts = ["Parsed subject/marks table from PDF."]
    if extra_subjects:
        extras = ", ".join(f"{x['name']} {x['score']}" for x in extra_subjects)
        notes_parts.append(f"Additional subjects (review): {extras}.")

    return {
        "student_name": student_name,
        "subject_scores": subject_scores,
        "extra_subjects": extra_subjects,
        "attendance_pct": None,
        "avg_score": avg_score,
        "narrative": narrative,
        "blooms": None,
        "sel": None,
        "confidence": "high",
        "notes": " ".join(notes_parts),
        "marks_only": True,
    }


def merge_pdf_extraction(heuristic: dict[str, Any], llm_data: dict[str, Any]) -> dict[str, Any]:
    """Prefer deterministic marks-table parse; let LLM fill gaps only."""
    merged = {**llm_data}
    for key in ("student_name", "narrative", "avg_score", "attendance_pct", "notes", "confidence"):
        if heuristic.get(key) not in (None, ""):
            merged[key] = heuristic[key]

    h_subj = heuristic.get("subject_scores") or {}
    l_subj = merged.get("subject_scores") or {}
    if not isinstance(l_subj, dict):
        l_subj = {}
    out_subj: dict[str, Any] = {}
    for bucket in ("maths", "science", "english", "social", "hindi", "sanskrit"):
        hv = h_subj.get(bucket) if isinstance(h_subj, dict) else None
        lv = l_subj.get(bucket) if isinstance(l_subj, dict) else None
        out_subj[bucket] = hv if hv is not None else lv
    merged["subject_scores"] = out_subj
    merged["extra_subjects"] = heuristic.get("extra_subjects") or llm_data.get("extra_subjects") or []
    if heuristic.get("blooms") is None:
        merged["blooms"] = None
    if heuristic.get("sel") is None:
        merged["sel"] = None
    merged["marks_only"] = True
    return merged


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_subject_scores(raw: Any) -> dict[str, Optional[float]]:
    keys = ("maths", "science", "english", "social", "hindi", "sanskrit")
    src = raw if isinstance(raw, dict) else {}
    return {k: _optional_float(src.get(k)) for k in keys}


def _normalize_blooms_sel(raw: Any, keys: tuple[str, ...]) -> Optional[dict[str, float]]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    out: dict[str, float] = {}
    for k in keys:
        v = _optional_float(raw.get(k))
        if v is not None:
            out[k] = v
    return out or None


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


def normalized_payload(
    extracted: dict[str, Any],
    quarter_hint: Optional[str],
    *,
    marks_only: bool = False,
) -> dict[str, Any]:
    quarter = (extracted.get("quarter") or quarter_hint or "Q4").upper()
    if quarter not in ("Q1", "Q2", "Q3", "Q4"):
        quarter = "Q4"

    risk = extracted.get("risk_level") or "Low"
    if risk not in ("Low", "Medium", "High"):
        risk = "Low"

    subject_scores = _normalize_subject_scores(extracted.get("subject_scores"))
    blooms = _normalize_blooms_sel(
        extracted.get("blooms"),
        ("remember", "understand", "apply", "analyse", "evaluate", "create"),
    )
    sel = _normalize_blooms_sel(
        extracted.get("sel"),
        (
            "self_awareness", "self_management", "social_awareness",
            "relationship_skills", "responsible_decisions",
        ),
    )

    attendance = _optional_float(extracted.get("attendance_pct"))
    avg_score = _optional_float(extracted.get("avg_score"))

    present_scores = [v for v in subject_scores.values() if v is not None]
    if avg_score is None and present_scores:
        avg_score = round(mean(present_scores), 2)

    # Full quarterly template: keep legacy zero defaults when not marks-only
    if not marks_only:
        if attendance is None:
            attendance = 0.0
        if avg_score is None:
            avg_score = 0.0
        subject_scores = {
            k: (subject_scores[k] if subject_scores[k] is not None else 0.0)
            for k in subject_scores
        }
        if blooms is None:
            blooms = {k: 0.0 for k in (
                "remember", "understand", "apply", "analyse", "evaluate", "create"
            )}
        if sel is None:
            sel = {k: 0.0 for k in (
                "self_awareness", "self_management", "social_awareness",
                "relationship_skills", "responsible_decisions",
            )}

    return {
        "quarter": quarter,
        "fy": extracted.get("fy") or "2025-26",
        "attendance_pct": attendance,
        "avg_score": avg_score,
        "risk_level": risk,
        "rank_in_class": extracted.get("rank_in_class"),
        "class_size": extracted.get("class_size"),
        "circle_name": extracted.get("circle_name"),
        "subject_scores": subject_scores,
        "blooms": blooms,
        "sel": sel,
        "narrative": (extracted.get("narrative") or "").strip(),
        "tutor_recommendation": extracted.get("tutor_recommendation"),
        "ready_for_zenk": bool(extracted.get("ready_for_zenk", True)),
        "marks_only": marks_only,
        "extra_subjects": extracted.get("extra_subjects") or [],
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
    heuristic = parse_marks_report_heuristics(text)
    extracted = await llm_extract_report_fields(
        text, students, hint_student_id=student_id, hint_quarter=quarter
    )
    marks_only = bool(heuristic)
    if heuristic:
        extracted = merge_pdf_extraction(heuristic, extracted)
    resolved_id = _resolve_student_id(extracted, students, student_id)
    payload = normalized_payload(extracted, quarter, marks_only=marks_only)

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
    review_draft = (review.payload or {}).get("draft") or {}
    validate_quarterly_payload(
        payload,
        partial=bool(payload.get("marks_only") or review_draft.get("marks_only")),
    )

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
