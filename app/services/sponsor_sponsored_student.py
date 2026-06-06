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
)
from app.models.student_family import ParentAcademicSubmission
from app.services.parent_portal import submission_brief_dict
from app.services.school_zqa_engine import get_zqa_breakdown
from app.services.student_circle_privacy import mask_student_for_circle


def _latest_quarter(rows: list, attr: str = "quarter") -> Optional[str]:
    order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    quarters = [getattr(r, attr, None) for r in rows if getattr(r, attr, None)]
    if not quarters:
        return None
    return max(quarters, key=lambda q: order.get((q or "Q0").split()[0], 0))


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
    q = quarter.upper()
    for r in rows:
        if (getattr(r, attr, None) or "").upper() == q:
            return r
    if rows:
        return sorted(rows, key=lambda x: getattr(x, attr, None) or "", reverse=True)[0]
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

    latest_q = (
        (quarter or "").upper()
        or _latest_quarter(subject_rows)
        or _latest_quarter(blooms_rows)
        or _latest_quarter(sel_rows)
        or _latest_quarter(narrative_rows)
        or "Q4"
    )

    subject_scores = [
        {
            "subject": r.subject,
            "quarter": r.quarter,
            "score": int(round(float(r.score or 0))),
        }
        for r in subject_rows
        if (r.quarter or "").upper() == latest_q
        or (r.quarter or "").upper().startswith(latest_q[:2])
    ]
    if not subject_scores:
        subject_scores = [
            {
                "subject": r.subject,
                "quarter": r.quarter,
                "score": int(round(float(r.score or 0))),
            }
            for r in sorted(subject_rows, key=lambda x: x.quarter or "", reverse=True)[:6]
        ]

    blooms_row = _row_for_quarter(blooms_rows, latest_q)
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

    sel_row = _row_for_quarter(sel_rows, latest_q)
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

    narrative_row = _row_for_quarter(narrative_rows, latest_q)
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
    if int(school_student.zqa_score or 0) > 0 or subject_scores:
        try:
            raw = await get_zqa_breakdown(db, school_student, latest_q)
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

    school_comment = (
        school_student.tutor_recommendation
        or (narrative["narrative"] if narrative else None)
        or "School records will appear after quarterly reports are submitted."
    )

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

    return {
        **base,
        "circle_name": school_student.circle_name,
        "mentor_name": school_student.mentor_name,
        "rank_in_class": school_student.rank_in_class,
        "class_size": school_student.class_size,
        "rank_display": rank_display,
        "improvement_pts": max(0, int(school_student.zqa_baseline_delta or 0)),
        "zenq_contribution": (
            float(school_student.zenq_contribution)
            if school_student.zenq_contribution is not None
            else None
        ),
        "latest_quarter": latest_q,
        "subject_scores": subject_scores,
        "blooms": blooms,
        "sel": sel,
        "narrative": narrative,
        "zqa_breakdown": zqa_breakdown,
        "school_comment": school_comment,
        "tutor_recommendation_status": school_student.tutor_recommendation_status,
        "has_zqa": int(school_student.zqa_score or 0) > 0,
        "privacy_note": _privacy_note_for_viewer(viewer),
        "parent_approved_uploads": parent_approved_uploads,
        "viewer": viewer,
        "read_only": viewer in ("student", "parent", "sponsor"),
    }


def _privacy_note_for_viewer(viewer: str) -> str:
    if viewer == "student":
        return "View only — your school updates official records. Parents can submit documents for principal review."
    if viewer == "parent":
        return "View only — submit marks or grades above for principal review. School owns official quarterly reports."
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
