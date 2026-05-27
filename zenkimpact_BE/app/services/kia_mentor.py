"""
Kia — Mentor Advisor Service
=============================
Kia acts as a personalized Mentoring Advisor here.
She references InspireIndex breakdown, session history, and circle assignments
to give actionable guidance to the mentor.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.kia import _call_llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Kia Mentor Constitution
# ---------------------------------------------------------------------------

_MENTOR_CONSTITUTION = """You are Kia, ZenK's Mentor Advisor.
You are speaking directly with a verified ZenK mentor — an accomplished professional
who volunteers their time to guide students in their sponsored circles.

YOUR ROLE:
- Help the mentor improve their InspireIndex score with specific, data-backed actions.
- Coach them on maximizing student engagement and session quality.
- Recognize their contributions warmly and celebrate milestones.
- Suggest community uplift actions appropriate to their tier.

TONE: Warm but professional. Treat them as a peer, not a student.
You respect their time — be concise and specific.

RULES:
1. Always base advice on the Mentor Context provided.
2. Reference InspireIndex sub-scores when giving improvement tips.
3. Never share one mentor's data with another mentor.
4. Student real names are never available to you — use circle names only.
5. If asked something outside your scope, politely redirect.
6. Keep responses under 3 short paragraphs for dashboard chat.

FORMATTING: Plain text only. No markdown, no bullet points, no headers.
When you have a suggestion, put it on its own line: "Kia suggests: [text]"
"""


def _build_mentor_system_prompt(mentor_context: dict) -> str:
    """Build full system prompt with mentor context injected."""
    prompt = _MENTOR_CONSTITUTION + "\n\n"

    if mentor_context:
        prompt += "--- MENTOR CONTEXT ---\n"
        for k, v in mentor_context.items():
            prompt += f"- {k.replace('_', ' ').title()}: {v}\n"
        prompt += "----------------------\n"
    else:
        prompt += "--- MENTOR CONTEXT ---\nNo context available.\n----------------------\n"

    return prompt


# ---------------------------------------------------------------------------
# Context Fetcher
# ---------------------------------------------------------------------------

from app.models.mentor import MentorProfile, MentorSession, MentorUpliftAction


async def fetch_mentor_context(user_id: str, db: AsyncSession) -> dict:
    """Fetch mentor metrics from DB to build Kia context."""
    stmt = select(MentorProfile).where(MentorProfile.id == user_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        return {}

    # Recent session count
    sessions_stmt = select(MentorSession).where(MentorSession.mentor_id == user_id)
    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    # InspireIndex breakdown summary
    breakdown = profile.inspire_breakdown or {}
    breakdown_summary = ", ".join(
        [f"{k.replace('_', ' ').title()}: {v} pts" for k, v in breakdown.items()]
    ) if breakdown else "Not yet computed"

    return {
        "mentor_name": "Mentor",
        "tier": f"Tier {profile.tier} — {profile.tier_label}",
        "specialty": profile.specialty,
        "city": profile.city,
        "assigned_circles": ", ".join(profile.assigned_circles or []) or "None assigned",
        "sessions_this_fy": profile.sessions_this_fy,
        "hours_mentored": f"{profile.hours_mentored} hrs",
        "inspire_index": f"{profile.inspire_index} / 100 (top {100 - profile.inspire_index_percentile}% of mentors)",
        "inspire_index_delta": f"+{profile.inspire_index_delta} pts this month",
        "inspire_breakdown": breakdown_summary,
        "zenq_contribution": f"+{profile.zenq_contribution}",
        "community_uplift_actions": profile.community_uplift_count,
        "recent_sessions_count": len(sessions),
    }


# ---------------------------------------------------------------------------
# Response Generators
# ---------------------------------------------------------------------------

async def generate_mentor_response(message: str, mentor_context: dict) -> Optional[str]:
    """Generate a Kia response for the mentor dashboard chat."""
    try:
        system_prompt = _build_mentor_system_prompt(mentor_context)
        return await _call_llm(
            system_prompt=system_prompt,
            user_message=message,
            max_tokens=1024,
            temperature=0.7,
        )
    except Exception as e:
        logger.error(f"kia_mentor: Error generating response: {e}")
        return None


async def generate_mentor_inspire_insight(mentor_context: dict) -> Optional[str]:
    """Generate a proactive Kia insight specifically about InspireIndex improvement.
    Returns plain text (not JSON).
    """
    try:
        system_prompt = _build_mentor_system_prompt(mentor_context)
        system_prompt += "\nYou are generating a single proactive insight about the mentor's InspireIndex. Be specific and reference their actual breakdown scores."

        prompt = (
            "Based on the mentor context provided, generate one concise, actionable insight "
            "about how this mentor can improve their InspireIndex score this month. "
            "Reference their specific sub-score breakdown. "
            "Format: 2-3 sentences max. End with one 'Kia suggests: ...' line."
        )

        return await _call_llm(
            system_prompt=system_prompt,
            user_message=prompt,
            max_tokens=300,
            temperature=0.5,
        )
    except Exception as e:
        logger.error(f"kia_mentor: Error generating inspire insight: {e}")
        return None
