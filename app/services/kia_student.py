"""Kia AI for student dashboard — safe, pseudonym-only context."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signup import SignupRequest
from app.services.kia import _call_llm
from app.services.student_dashboard import build_student_overview, build_student_progress

logger = logging.getLogger(__name__)

_STUDENT_KIA_PROMPT = """You are Kia, the AI learning companion for a ZenK sponsored student.

RULES (CRITICAL):
- Address the student by their pseudonym only. Never use or guess their real name.
- Share only THEIR progress (ZQA, attendance, grades) — never other students' data.
- Never share sponsor financial contributions, addresses, or contact details.
- Never suggest meeting sponsors outside the platform.
- Be warm, age-appropriate, encouraging. Keep answers under 3 short paragraphs.
- If data is missing, say school/circle linking is in progress — stay positive.
- Suggest study habits, goal-setting, and how to use circle mentoring (text for now).
- Do NOT mention video/voice calls as available — say "text mentoring" is available now.

STUDENT CONTEXT:
{context_block}
"""


async def fetch_student_context(db: AsyncSession, signup: SignupRequest) -> dict:
    overview = await build_student_overview(db, signup)
    progress = await build_student_progress(db, signup)
    kpis = overview.get("kpis") or {}
    lines = [
        f"pseudonym: {overview.get('pseudonym')}",
        f"grade: {overview.get('grade') or 'N/A'}",
        f"school_linked: {overview.get('school_linked')}",
        f"circle: {overview.get('circle_name_masked') or 'not connected'}",
        f"zqa_score: {kpis.get('zqa_score', 0)}",
        f"attendance_pct: {kpis.get('attendance_pct', 0)}",
        f"avg_score: {kpis.get('avg_score', 0)}",
        f"risk_level: {kpis.get('risk_level', '—')}",
        f"login_access_tier: {overview.get('login_access_tier')}",
        f"has_parental_consent: {overview.get('has_parental_consent')}",
    ]
    if progress.get("linked") and progress.get("breakdown"):
        hol = progress["breakdown"].get("holistic_score")
        if hol is not None:
            lines.append(f"holistic_zqa: {hol}")
    if overview.get("school_note"):
        lines.append(f"teacher_note: {overview['school_note'][:200]}")
    return {"context_block": "\n".join(lines), "overview": overview}


async def generate_student_response(
    message: str,
    student_context: dict,
) -> Optional[str]:
    try:
        system_prompt = _STUDENT_KIA_PROMPT.format(
            context_block=student_context.get("context_block", "")
        )
        return await _call_llm(
            system_prompt=system_prompt,
            user_message=message,
            max_tokens=512,
            temperature=0.6,
        )
    except Exception as exc:
        logger.error("kia_student: LLM error: %s", exc)
        return None


async def generate_student_priorities(db: AsyncSession, signup: SignupRequest) -> list[dict]:
    overview = await build_student_overview(db, signup)
    kpis = overview.get("kpis") or {}
    items: list[dict] = []

    if not overview.get("school_linked"):
        items.append({
            "type": "onboarding",
            "title": "School link pending",
            "detail": "Your ZQA and attendance appear once your school confirms enrollment.",
            "urgency": "This week",
        })
    if not overview.get("circle_id"):
        items.append({
            "type": "circle",
            "title": "Circle connection",
            "detail": "Ask your parent/guardian to complete circle membership approval.",
            "urgency": "This week",
        })
    if kpis.get("attendance_pct", 0) and kpis["attendance_pct"] < 75:
        items.append({
            "type": "attendance",
            "title": "Attendance focus",
            "detail": f"You're at {kpis['attendance_pct']}% — small daily habits help.",
            "urgency": "Immediate",
        })
    if not overview.get("has_parental_consent") and overview.get("login_access_tier") != "independent":
        items.append({
            "type": "consent",
            "title": "Parental consent",
            "detail": "Chat features need verified guardian consent (DPDPA).",
            "urgency": "Before chat",
        })
    if kpis.get("zqa_score", 0) >= 70:
        items.append({
            "type": "milestone",
            "title": "Strong ZQA",
            "detail": "Keep engaging with mentoring and circle activities.",
            "urgency": "This term",
        })
    if not items:
        items.append({
            "type": "welcome",
            "title": "Welcome to ZenK",
            "detail": "Explore mentoring, track progress, and chat with Kia anytime.",
            "urgency": "Today",
        })
    return items[:5]
