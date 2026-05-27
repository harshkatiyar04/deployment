"""Parse and apply quarterly report CSV uploads for school dashboard."""

from __future__ import annotations

import csv
import io
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import SchoolStudent
from app.models.signup import SignupRequest
from app.services.school_reports import apply_quarterly_report

CSV_HEADERS = [
    "student_id",
    "student_name",
    "quarter",
    "fy",
    "attendance_pct",
    "avg_score",
    "risk_level",
    "rank_in_class",
    "class_size",
    "circle_name",
    "maths",
    "science",
    "english",
    "social",
    "hindi",
    "sanskrit",
    "blooms_remember",
    "blooms_understand",
    "blooms_apply",
    "blooms_analyse",
    "blooms_evaluate",
    "blooms_create",
    "sel_self_awareness",
    "sel_self_management",
    "sel_social_awareness",
    "sel_relationship_skills",
    "sel_responsible_decisions",
    "narrative",
    "tutor_recommendation",
    "ready_for_zenk",
]


def csv_template_text(students: list[SchoolStudent]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_HEADERS)
    if students:
        s = students[0]
        writer.writerow([
            s.id,
            s.full_name,
            "Q4",
            "2025-26",
            "", "", "Low", "", "", "",
            "", "", "", "", "", "",
            "", "", "", "", "", "",
            "", "", "", "", "",
            "",
            "",
            "yes",
        ])
    else:
        writer.writerow([""] * len(CSV_HEADERS))
    return buf.getvalue()


def _norm_key(key: str) -> str:
    return (key or "").strip().lower().replace(" ", "_").replace("-", "_")


def _row_dict(raw: dict[str, str]) -> dict[str, str]:
    return {_norm_key(k): (v or "").strip() for k, v in raw.items()}


def _parse_float(val: str, field: str, lo: float, hi: float) -> float:
    if val == "":
        raise ValueError(f"{field} is required")
    num = float(val)
    if num < lo or num > hi:
        raise ValueError(f"{field} must be between {lo} and {hi}")
    return num


def _parse_optional_float(val: str, field: str, lo: float, hi: float) -> Optional[float]:
    if val == "":
        return None
    num = float(val)
    if num < lo or num > hi:
        raise ValueError(f"{field} must be between {lo} and {hi}")
    return num


def _parse_bool(val: str) -> bool:
    if val == "":
        return True
    v = val.strip().lower()
    if v in ("yes", "y", "true", "1", "finalized", "final"):
        return True
    if v in ("no", "n", "false", "0", "draft", "pending"):
        return False
    raise ValueError("ready_for_zenk must be yes/no")


def _build_payload(row: dict[str, str]) -> dict[str, Any]:
    quarter = row.get("quarter", "").upper()
    if quarter not in ("Q1", "Q2", "Q3", "Q4"):
        raise ValueError("quarter must be Q1, Q2, Q3, or Q4")

    risk = row.get("risk_level", "Low") or "Low"
    if risk not in ("Low", "Medium", "High"):
        raise ValueError("risk_level must be Low, Medium, or High")

    class_size_raw = row.get("class_size", "")
    class_size = int(class_size_raw) if class_size_raw else None

    return {
        "quarter": quarter,
        "fy": row.get("fy") or "2025-26",
        "attendance_pct": _parse_float(row.get("attendance_pct", ""), "attendance_pct", 0, 100),
        "avg_score": _parse_float(row.get("avg_score", ""), "avg_score", 0, 100),
        "risk_level": risk,
        "rank_in_class": row.get("rank_in_class") or None,
        "class_size": class_size,
        "circle_name": row.get("circle_name") or None,
        "subject_scores": {
            "maths": _parse_float(row.get("maths", ""), "maths", 0, 100),
            "science": _parse_float(row.get("science", ""), "science", 0, 100),
            "english": _parse_float(row.get("english", ""), "english", 0, 100),
            "social": _parse_float(row.get("social", ""), "social", 0, 100),
            "hindi": _parse_float(row.get("hindi", ""), "hindi", 0, 100),
            "sanskrit": _parse_optional_float(row.get("sanskrit", ""), "sanskrit", 0, 100),
        },
        "blooms": {
            "remember": _parse_float(row.get("blooms_remember", ""), "blooms_remember", 0, 5),
            "understand": _parse_float(row.get("blooms_understand", ""), "blooms_understand", 0, 5),
            "apply": _parse_float(row.get("blooms_apply", ""), "blooms_apply", 0, 5),
            "analyse": _parse_float(row.get("blooms_analyse", ""), "blooms_analyse", 0, 5),
            "evaluate": _parse_float(row.get("blooms_evaluate", ""), "blooms_evaluate", 0, 5),
            "create": _parse_float(row.get("blooms_create", ""), "blooms_create", 0, 5),
        },
        "sel": {
            "self_awareness": _parse_float(row.get("sel_self_awareness", ""), "sel_self_awareness", 0, 5),
            "self_management": _parse_float(row.get("sel_self_management", ""), "sel_self_management", 0, 5),
            "social_awareness": _parse_float(row.get("sel_social_awareness", ""), "sel_social_awareness", 0, 5),
            "relationship_skills": _parse_float(
                row.get("sel_relationship_skills", ""), "sel_relationship_skills", 0, 5
            ),
            "responsible_decisions": _parse_float(
                row.get("sel_responsible_decisions", ""), "sel_responsible_decisions", 0, 5
            ),
        },
        "narrative": row.get("narrative") or "",
        "tutor_recommendation": row.get("tutor_recommendation") or None,
        "ready_for_zenk": _parse_bool(row.get("ready_for_zenk", "")),
    }


def _resolve_student(
    row: dict[str, str],
    by_id: dict[str, SchoolStudent],
    by_name: dict[str, SchoolStudent],
) -> SchoolStudent:
    sid = row.get("student_id", "")
    if sid:
        student = by_id.get(sid)
        if student:
            return student
        raise ValueError(f"student_id not found: {sid}")

    name = row.get("student_name", "")
    if name:
        student = by_name.get(name.strip().lower())
        if student:
            return student
        raise ValueError(f"student_name not found: {name}")

    raise ValueError("student_id or student_name is required")


async def import_quarterly_csv(
    db: AsyncSession,
    *,
    school_id: str,
    user: SignupRequest,
    file_bytes: bytes,
) -> dict[str, Any]:
    try:
        decoded = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("CSV must be UTF-8 encoded") from e

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise ValueError("CSV is empty or missing a header row")

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == school_id)
    )
    students = students_res.scalars().all()
    by_id = {s.id: s for s in students}
    by_name = {s.full_name.strip().lower(): s for s in students}

    success_count = 0
    errors: list[str] = []
    imported: list[dict[str, str]] = []

    for row_idx, raw in enumerate(reader, start=2):
        row = _row_dict(raw)
        if not any(row.values()):
            continue
        sid = row.get("student_id", "")
        if sid.startswith("#") or sid.lower() in ("instructions", "example"):
            continue
        try:
            if not (row.get("narrative") or "").strip():
                raise ValueError("narrative is required")

            student = _resolve_student(row, by_id, by_name)
            payload = _build_payload(row)
            submission = await apply_quarterly_report(
                db,
                school_id=school_id,
                student=student,
                user=user,
                payload=payload,
                source="csv",
            )
            success_count += 1
            imported.append({
                "row": str(row_idx),
                "student_name": student.full_name,
                "quarter": payload["quarter"],
                "submission_id": submission.id,
            })
        except Exception as e:
            errors.append(f"Row {row_idx}: {e}")

    if success_count > 0:
        await db.commit()
    else:
        await db.rollback()

    return {
        "status": "success" if success_count else "failed",
        "message": (
            f"Imported {success_count} report row(s)."
            if success_count
            else "No rows imported. Fix errors and try again."
        ),
        "success_count": success_count,
        "errors": errors,
        "imported": imported,
    }
