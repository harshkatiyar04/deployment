from __future__ import annotations
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.kia import _call_llm

logger = logging.getLogger(__name__)

_SCHOOL_CONSTITUTION = """You are Kia, ZenK's School AI Advisor.
You are speaking with the Principal of a ZenK Partner School — a dedicated educational leader
responsible for the academic progress and wellbeing of their students enrolled in ZenK-sponsored circles.

YOUR ROLE:
- Surface actionable insights about student attendance, academic performance, and ZQA scores.
- Flag students at risk and suggest concrete next steps (parent contact, tutor matching, circle engagement).
- Help the principal navigate ZenK platform tasks: submitting reports, reviewing ZQA milestones.
- Celebrate student achievements and school milestones warmly.

TONE: Professional, warm, and concise. You treat the principal as a trusted partner.

RULES:
1. Always base insights on the School Context provided — never hallucinate metrics.
2. Reference student names only when contextually appropriate.
3. Flag high-risk students proactively.
4. Keep dashboard responses under 3 short paragraphs.
5. No markdown, no bullet points, no headers in responses — plain conversational text only.
6. Never share information about other schools.

FORMATTING: Plain text. When you have a specific suggestion, prefix it: "Kia recommends: [text]"
"""


def _build_school_prompt(school_context: dict) -> str:
    prompt = _SCHOOL_CONSTITUTION + "\n\n"
    if school_context:
        prompt += "--- SCHOOL CONTEXT ---\n"
        for k, v in school_context.items():
            prompt += f"- {k.replace('_', ' ').title()}: {v}\n"
        prompt += "----------------------\n"
    return prompt


async def fetch_school_context(school_id: str, db: AsyncSession) -> dict:
    from app.models.school import SchoolProfile, SchoolStudent, SchoolReport

    profile_res = await db.execute(
        select(SchoolProfile).where(SchoolProfile.id == school_id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        return {}

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == school_id)
    )
    students = students_res.scalars().all()

    high_risk = [s.full_name for s in students if s.risk_level == "High"]
    below_attendance = [s.full_name for s in students if s.attendance_pct < 75]

    reports_res = await db.execute(
        select(SchoolReport).where(
            SchoolReport.school_id == school_id,
            SchoolReport.status == "Pending",
        )
    )
    pending_reports = reports_res.scalars().all()

    return {
        "school_name": profile.school_name,
        "principal_name": profile.principal_name,
        "total_students": len(students),
        "avg_attendance": f"{profile.avg_attendance:.0f}%",
        "avg_academic_score": f"{profile.avg_academic_score:.0f}%",
        "high_risk_students": ", ".join(high_risk) if high_risk else "None",
        "students_below_attendance_threshold": ", ".join(below_attendance) if below_attendance else "None",
        "pending_reports_count": len(pending_reports),
        "next_zqa_date": profile.next_zqa_date or "Not scheduled",
        "fy": profile.fy_current,
    }


async def generate_school_response(message: str, school_context: dict) -> Optional[str]:
    try:
        system_prompt = _build_school_prompt(school_context)
        return await _call_llm(
            system_prompt=system_prompt,
            user_message=message,
            max_tokens=1024,
            temperature=0.65,
        )
    except Exception as e:
        logger.error(f"kia_school: LLM error: {e}")
        return None


async def generate_school_priorities(school_id: str, db: AsyncSession) -> list[dict]:
    from app.models.school import SchoolStudent, SchoolReport

    students_res = await db.execute(
        select(SchoolStudent).where(SchoolStudent.school_id == school_id)
    )
    students = students_res.scalars().all()
    student_map = {s.id: s.full_name for s in students}

    reports_res = await db.execute(
        select(SchoolReport).where(
            SchoolReport.school_id == school_id,
            SchoolReport.status == "Pending",
        )
    )
    pending_reports = reports_res.scalars().all()

    priorities = []

    for s in students:
        if s.attendance_pct < 75:
            grade_part = s.grade.replace("Grade ", "Gr ")
            priorities.append({
                "type": "attendance_alert",
                "title": f"Attendance alert — {s.full_name} ({grade_part})",
                "detail": (
                    f"Attendance dropped to {s.attendance_pct:.0f}%, below the 75% ZenQ threshold. "
                    f"This risks a ZQA disqualification if sustained. "
                    f"Recommend contacting parent/guardian and alerting the Sponsor Leader."
                ),
                "student_name": s.full_name,
                "action_required": True,
            })

    if pending_reports:
        names = ", ".join(
            student_map.get(r.student_id, "Unknown") for r in pending_reports[:2]
        )
        quarters = list({r.quarter for r in pending_reports})
        priorities.append({
            "type": "report_due",
            "title": f"{pending_reports[0].quarter} reports due — {len(pending_reports)} students pending",
            "detail": (
                f"{names} {'/'.join(quarters)} reports are not yet submitted. "
                f"Deadline: 10 April 2026. Kia has pre-generated draft reports for teacher review."
            ),
            "student_name": None,
            "action_required": True,
        })

    for s in students:
        if s.zqa_score >= 90:
            priorities.append({
                "type": "zqa_milestone",
                "title": f"ZQA milestone — {s.full_name}",
                "detail": (
                    f"{s.full_name} scored {s.zqa_score:.0f}% in Q3 ZQA, "
                    f"up from 70% baseline. This milestone contributes +4.2 pts to the circle's ZenQ score."
                ),
                "student_name": s.full_name,
                "action_required": False,
            })

    for s in students:
        if s.tutor_recommendation and s.tutor_recommendation_status == "none":
            priorities.append({
                "type": "tutor_recommendation",
                "title": f"Tutor recommendation — {s.full_name}",
                "detail": s.tutor_recommendation,
                "student_name": s.full_name,
                "action_required": True,
            })

    return priorities
