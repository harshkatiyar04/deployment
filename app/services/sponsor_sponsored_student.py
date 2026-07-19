"""Full pseudonym-first sponsored student profile for sponsor circle dashboards."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import (
    SchoolStudent,
    SchoolStudentBloomsAssessment,
    SchoolStudentNarrative,
    SchoolStudentSEL,
    SchoolStudentSubjectScore,
    SchoolZqaSnapshot,
)
from app.models.student_family import ParentAcademicSubmission
from app.services.parent_portal import submission_brief_dict
from app.services.school_zqa_engine import get_zqa_breakdown
from app.services.student_circle_privacy import mask_student_for_circle


_QUARTER_ORDER = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}


def _quarter_key(quarter: Optional[str]) -> str:
    return ((quarter or "").strip().upper()[:2] or "Q0")


def _latest_quarter(rows: list, attr: str = "quarter") -> Optional[str]:
    quarters = [_quarter_key(getattr(r, attr, None)) for r in rows if getattr(r, attr, None)]
    quarters = [q for q in quarters if q in _QUARTER_ORDER]
    if not quarters:
        return None
    return max(quarters, key=lambda q: _QUARTER_ORDER[q])


def _quarters_with_records(
    subject_rows: list,
    blooms_rows: list,
    sel_rows: list,
    narrative_rows: list,
    snapshot_quarters: list[str],
) -> set[str]:
    found: set[str] = set()
    for rows in (subject_rows, blooms_rows, sel_rows, narrative_rows):
        for row in rows:
            q = _quarter_key(getattr(row, "quarter", None))
            if q in _QUARTER_ORDER:
                found.add(q)
    for q in snapshot_quarters:
        key = _quarter_key(q)
        if key in _QUARTER_ORDER:
            found.add(key)
    return found


def _quarter_status_message(requested: str, quarters_with_data: set[str]) -> tuple[str, str]:
    rq = _quarter_key(requested)
    if rq in quarters_with_data:
        return "published", ""

    if not quarters_with_data:
        return (
            "no_records",
            "Your school has not published any quarterly reports yet. "
            f"Records for {rq} will appear here after your school submits them.",
        )

    latest = max(quarters_with_data, key=lambda q: _QUARTER_ORDER[q])
    if _QUARTER_ORDER[rq] > _QUARTER_ORDER[latest]:
        return (
            "future",
            f"{rq} reports will be published by your school later this academic year.",
        )

    return (
        "not_published",
        f"No records for {rq} yet. Your school has not updated this quarter.",
    )


def _sanitize_zqa_breakdown(payload: dict[str, Any], pseudonym: str) -> dict[str, Any]:
    out = {k: v for k, v in payload.items() if k not in ("student_name", "student_id")}
    out["pseudonym"] = pseudonym
    snap = out.get("student_record_snapshot")
    if isinstance(snap, dict):
        out["student_record_snapshot"] = {
            k: v for k, v in snap.items() if k != "student_name"
        }
    return out


def _row_for_quarter(rows: list, quarter: str, attr: str = "quarter"):
    q = _quarter_key(quarter)
    for r in rows:
        if _quarter_key(getattr(r, attr, None)) == q:
            return r
    return None


async def build_sponsored_student_profile(
    db: AsyncSession,
    school_student: SchoolStudent,
    *,
    quarter: Optional[str] = None,
    viewer: str = "sponsor",
) -> dict[str, Any]:
    base = await mask_student_for_circle(db, school_student)
    pseudonym = base["pseudonym"]
    if viewer == "admin":
        base = {
            **base,
            "full_name": school_student.full_name,
            "legal_name": school_student.full_name,
        }

    subj_res = await db.execute(
        select(SchoolStudentSubjectScore).where(
            SchoolStudentSubjectScore.student_id == school_student.id
        )
    )
    subject_rows = list(subj_res.scalars().all())

    blooms_res = await db.execute(
        select(SchoolStudentBloomsAssessment).where(
            SchoolStudentBloomsAssessment.student_id == school_student.id
        )
    )
    blooms_rows = list(blooms_res.scalars().all())

    sel_res = await db.execute(
        select(SchoolStudentSEL).where(SchoolStudentSEL.student_id == school_student.id)
    )
    sel_rows = list(sel_res.scalars().all())

    narrative_res = await db.execute(
        select(SchoolStudentNarrative).where(
            SchoolStudentNarrative.student_id == school_student.id
        )
    )
    narrative_rows = list(narrative_res.scalars().all())

    snap_res = await db.execute(
        select(SchoolZqaSnapshot.quarter).where(
            SchoolZqaSnapshot.student_id == school_student.id
        )
    )
    snapshot_quarters = list(snap_res.scalars().all())

    quarters_with_data = _quarters_with_records(
        subject_rows,
        blooms_rows,
        sel_rows,
        narrative_rows,
        snapshot_quarters,
    )

    display_q = (
        _quarter_key(quarter)
        if quarter
        else (
            _latest_quarter(subject_rows)
            or _latest_quarter(blooms_rows)
            or _latest_quarter(sel_rows)
            or _latest_quarter(narrative_rows)
            or _quarter_key(snapshot_quarters[0] if snapshot_quarters else None)
            or "Q4"
        )
    )
    if display_q not in _QUARTER_ORDER:
        display_q = "Q4"

    quarter_status, quarter_message = _quarter_status_message(display_q, quarters_with_data)
    has_quarter_data = quarter_status == "published"

    subject_scores = [
        {
            "subject": r.subject,
            "quarter": r.quarter,
            "score": int(round(float(r.score or 0))),
        }
        for r in subject_rows
        if _quarter_key(r.quarter) == display_q
    ]

    blooms_row = _row_for_quarter(blooms_rows, display_q) if has_quarter_data else None
    blooms = (
        {
            "quarter": blooms_row.quarter,
            "remember": float(blooms_row.remember or 0),
            "understand": float(blooms_row.understand or 0),
            "apply": float(blooms_row.apply or 0),
            "analyse": float(blooms_row.analyse or 0),
            "evaluate": float(blooms_row.evaluate or 0),
            "create": float(blooms_row.create or 0),
        }
        if blooms_row
        else None
    )

    sel_row = _row_for_quarter(sel_rows, display_q) if has_quarter_data else None
    sel = (
        {
            "quarter": sel_row.quarter,
            "self_awareness": float(sel_row.self_awareness or 0),
            "self_management": float(sel_row.self_management or 0),
            "social_awareness": float(sel_row.social_awareness or 0),
            "relationship_skills": float(sel_row.relationship_skills or 0),
            "responsible_decisions": float(sel_row.responsible_decisions or 0),
        }
        if sel_row
        else None
    )

    narrative_row = _row_for_quarter(narrative_rows, display_q) if has_quarter_data else None
    narrative = (
        {
            "quarter": narrative_row.quarter,
            "teacher_name": narrative_row.teacher_name,
            "narrative": narrative_row.narrative,
            "finalized": bool(narrative_row.finalized),
        }
        if narrative_row and narrative_row.narrative
        else None
    )

    zqa_breakdown = None
    if has_quarter_data and (subject_scores or blooms_row or sel_row):
        try:
            raw = await get_zqa_breakdown(db, school_student, display_q)
            if viewer == "admin":
                zqa_breakdown = {
                    **raw,
                    "pseudonym": pseudonym,
                    "full_name": school_student.full_name,
                }
            else:
                zqa_breakdown = _sanitize_zqa_breakdown(raw, pseudonym)
        except Exception:
            zqa_breakdown = None

    rank_display = None
    if school_student.rank_in_class or school_student.class_size:
        raw_rank = (school_student.rank_in_class or "").strip()
        if raw_rank and school_student.class_size:
            rank_display = f"{raw_rank} / {school_student.class_size}"
        else:
            rank_display = raw_rank or None

    if has_quarter_data:
        school_comment = (
            (narrative["narrative"] if narrative else None)
            or school_student.tutor_recommendation
            or "School records will appear after quarterly reports are submitted."
        )
    else:
        school_comment = quarter_message

    parent_approved_uploads: list[dict[str, Any]] = []
    if school_student.signup_request_id:
        parent_res = await db.execute(
            select(ParentAcademicSubmission)
            .where(
                ParentAcademicSubmission.student_signup_id == school_student.signup_request_id,
                ParentAcademicSubmission.status == "approved",
            )
            .order_by(ParentAcademicSubmission.reviewed_at.desc())
            .limit(5)
        )
        parent_approved_uploads = [
            submission_brief_dict(sub) for sub in parent_res.scalars().all()
        ]

    quarter_avg_score = None
    if subject_scores:
        quarter_avg_score = int(
            round(sum(s["score"] for s in subject_scores) / len(subject_scores))
        )

    payload: dict[str, Any] = {
        **base,
        "circle_name": school_student.circle_name,
        "mentor_name": school_student.mentor_name,
        "rank_in_class": school_student.rank_in_class if has_quarter_data else None,
        "class_size": school_student.class_size if has_quarter_data else None,
        "rank_display": rank_display if has_quarter_data else None,
        "improvement_pts": max(0, int(school_student.zqa_baseline_delta or 0))
        if has_quarter_data
        else None,
        "zenq_contribution": (
            float(school_student.zenq_contribution)
            if has_quarter_data and school_student.zenq_contribution is not None
            else None
        ),
        "quarter": display_q,
        "latest_quarter": display_q,
        "quarter_status": quarter_status,
        "quarter_message": quarter_message,
        "quarters_with_data": sorted(quarters_with_data, key=lambda q: _QUARTER_ORDER[q]),
        "subject_scores": subject_scores,
        "blooms": blooms,
        "sel": sel,
        "narrative": narrative,
        "zqa_breakdown": zqa_breakdown,
        "school_comment": school_comment,
        "tutor_recommendation_status": school_student.tutor_recommendation_status,
        "has_zqa": has_quarter_data and int(school_student.zqa_score or 0) > 0,
        "privacy_note": _privacy_note_for_viewer(viewer),
        "parent_approved_uploads": parent_approved_uploads,
        "viewer": viewer,
        "read_only": viewer in ("student", "parent", "sponsor", "admin"),
    }

    if has_quarter_data:
        if quarter_avg_score is not None:
            payload["avg_score"] = quarter_avg_score
    else:
        # Keep live roster KPIs visible for admin even when a quarter has no published rows.
        if viewer == "admin":
            payload["attendance_pct"] = int(school_student.attendance_pct or 0)
            payload["avg_score"] = int(school_student.avg_score or 0)
            payload["zqa_score"] = int(round(float(school_student.zqa_score or 0)))
            payload["risk_level"] = school_student.risk_level
        else:
            payload["attendance_pct"] = None
            payload["avg_score"] = None
            payload["zqa_score"] = None
            payload["risk_level"] = None

    return payload


def _privacy_note_for_viewer(viewer: str) -> str:
    if viewer == "student":
        return "View only — your school updates official records. Parents can submit documents for principal review."
    if viewer == "parent":
        return "View only — submit marks or grades above for principal review. School owns official quarterly reports."
    if viewer == "admin":
        return "Platform admin view — legal name and full academic records are visible for progress tracking."
    return "Identity is masked. Only your school principal sees the student's legal name."


async def sponsored_student_profile_for_circle(
    db: AsyncSession,
    circle_id: str,
    *,
    quarter: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    res = await db.execute(
        select(SchoolStudent)
        .where(SchoolStudent.circle_id == circle_id)
        .order_by(SchoolStudent.created_at.desc())
        .limit(1)
    )
    row = res.scalar_one_or_none()
    if not row:
        return None
    return await build_sponsored_student_profile(db, row, quarter=quarter, viewer="sponsor")
