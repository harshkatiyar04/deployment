"""
Kia RAG Context Fetcher
=======================
Builds a personalized data context for the requesting user so Kia can answer
questions about their own data (participation, circle rank, time spent, etc.)

Privacy Architecture:
  - All queries are scoped to `user_id` of the *requesting* user only.
  - Contribution / budget data is flagged as PRIVATE and never returned for
    other users' IDs.
  - The returned dict is injected into Kia's system prompt before the user's
    question, grounding Kia in real (or structured placeholder) data.

Swap Guide (when real DB data is ready):
  - Replace the `_fetch_*_hardcoded()` helpers with real `await db.execute(...)` queries.
  - The `fetch_user_context()` signature and return schema stay identical.
  - No changes needed in kia.py or router_client.py.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hardcoded data layer (replace with real DB queries when ready)
# ---------------------------------------------------------------------------

# Simulates per-user participation data keyed by user_id.
# TODO: Replace with: SELECT participation_pct FROM ZENK.member_stats WHERE user_id = :uid AND circle_id = :cid
_HARDCODED_PARTICIPATION: dict[str, int] = {}  # user_id -> pct (defaults to 74 if not found)
_DEFAULT_PARTICIPATION = 74
_CIRCLE_AVG_PARTICIPATION = 68

# Simulates per-user ZenQ / rank data.
# TODO: Replace with: SELECT zenq_score, circle_rank FROM ZENK.member_scores WHERE user_id = :uid
_HARDCODED_ZENQ: dict[str, dict] = {}
_DEFAULT_ZENQ = {"zenq_score": 82, "circle_rank": 3, "total_circles": 47, "zenq_change": 4, "rank_previous": 5}

# Simulates per-user time spent data.
# TODO: Replace with: SELECT time_this_month_hrs FROM ZENK.time_logs WHERE user_id = :uid
_HARDCODED_TIME: dict[str, float] = {}
_DEFAULT_TIME_HRS = 6.5
_TOP_GROUP_HRS = 11.2

# Circle-level rankings (public, not user-scoped)
# TODO: Replace with: SELECT rank, name, zenq_score, city FROM ZENK.circle_rankings ORDER BY rank
_CIRCLE_RANKINGS = [
    {"rank": 1, "name": "Vasundhara Circle", "city": "Pune", "zenq": 96},
    {"rank": 2, "name": "Prarambh Mumbai", "city": "Mumbai", "zenq": 89},
    {"rank": 3, "name": "Ashoka Rising", "city": "Mumbai", "zenq": 82, "is_mine": True},
    {"rank": 4, "name": "Udaan Bangalore", "city": "Bengaluru", "zenq": 78},
    {"rank": 5, "name": "Kishore Circle", "city": "Delhi", "zenq": 71},
]

# Circle-level budget data (public within the circle)
# Matches the data in app/microservices/sponsor_circle/router.py
_CIRCLE_BUDGET_SUMMARY = {
    "total_budget": 150000,
    "spent": 94200,
    "collected": 124500,
    "balance_to_spend": 55800,
    "fy_label": "FY 2025-26",
}

# Per-user contribution data (PRIVATE — only return for the requesting user)
# TODO: Replace with: SELECT amount, month FROM ZENK.contributions WHERE user_id = :uid ORDER BY month DESC
_HARDCODED_CONTRIBUTIONS: dict[str, dict] = {}
_DEFAULT_CONTRIBUTION = {
    "total_contributed": 15000,  # INR
    "this_month": 2500,
    "currency": "INR",
    "note": "Thank you for your consistent support!"
}

# Sponsored Student Data (Shared within the circle)
# TODO: Replace with: SELECT * FROM ZENK.students WHERE circle_id = :cid
_SPONSORED_STUDENT_DATA = {
    "name": "Ananya",
    "grade": "9th Standard",
    "school": "St. Mary's High School",
    "attendance_pct": 94,
    "recent_grades": {"Math": "A", "Science": "A-", "English": "B+"},
    "teacher_notes": "Ananya is showing great interest in robotics and computer science. Her attendance is consistent.",
    "zenq_score": 88,
    "impact_summary": "Your circle's support has enabled her to attend extra computer science classes and robotics club."
}


# All member contributions (LEADER-ONLY DATA — never shown to regular members)
# TODO: Replace with: SELECT u.full_name, SUM(c.amount) FROM ZENK.contributions c JOIN ZENK.signup_requests u ON c.user_id = u.id WHERE c.circle_id = :cid GROUP BY u.id
_ALL_MEMBER_CONTRIBUTIONS = [
    {"name": "Rohit Chawla", "role": "Coordinator", "total_contributed": 45000, "this_month": 8000, "pct_of_total": 36},
    {"name": "Priya Sharma", "role": "Sponsor Member", "total_contributed": 28000, "this_month": 8000, "pct_of_total": 22},
    {"name": "Arjun Kulkarni", "role": "Sponsor Member", "total_contributed": 22000, "this_month": 10000, "pct_of_total": 18},
    {"name": "Sneha Mehta", "role": "Mentor", "total_contributed": 15500, "this_month": 5000, "pct_of_total": 12},
    {"name": "Vikram Patil", "role": "CSR — TCS", "total_contributed": 36000, "this_month": 0, "pct_of_total": 29},
    {"name": "Mrs. Devika", "role": "Guardian (Parent)", "total_contributed": 4000, "this_month": 0, "pct_of_total": 3},
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_user_context(
    user_id: str,
    circle_id: str,
    db: AsyncSession,
    include_private: bool = True,  # True = requesting user asking about themselves
    is_leader: bool = False,  # True = Circle Leader — gets full member contribution access
) -> dict:
    """
    Build a personalized context dict for the requesting user.

    Parameters:
        user_id: The authenticated user's ID (from JWT).
        circle_id: The circle they're chatting in.
        db: Active async DB session.
        include_private: If True, includes contribution/budget data.
                         Always True when the user asks about themselves.
        is_leader: If True, includes ALL member contribution data.
                   This is the leader-exclusive data access layer.

    Returns:
        A structured dict injected into Kia's system prompt context block.
    """
    try:
        # 1. Resolve circle name
        circle_name = await _get_circle_name(circle_id, db)

        # 2. Get membership role
        role = await _get_member_role(user_id, circle_id, db)
        # Override role if leader flag is set
        if is_leader:
            role = "coordinator"

        # 3. Per-user stats (scoped, privacy-safe)
        participation = _HARDCODED_PARTICIPATION.get(user_id, _DEFAULT_PARTICIPATION)
        zenq_data = _HARDCODED_ZENQ.get(user_id, _DEFAULT_ZENQ)
        time_hrs = _HARDCODED_TIME.get(user_id, _DEFAULT_TIME_HRS)

        context = {
            "circle_name": circle_name,
            "member_role": role,
            # Participation
            "my_participation_pct": participation,
            "circle_avg_participation_pct": _CIRCLE_AVG_PARTICIPATION,
            "participation_vs_avg": participation - _CIRCLE_AVG_PARTICIPATION,
            # ZenQ / Circle Rank
            "my_zenq_score": zenq_data["zenq_score"],
            "my_circle_rank": zenq_data["circle_rank"],
            "total_circles_nationally": zenq_data["total_circles"],
            "zenq_change_this_month": zenq_data["zenq_change"],
            "previous_rank": zenq_data["rank_previous"],
            # Time
            "my_time_this_month_hrs": time_hrs,
            "top_group_time_hrs": _TOP_GROUP_HRS,
            "time_gap_to_top_hrs": round(_TOP_GROUP_HRS - time_hrs, 1),
            # Circle rankings (public)
            "national_circle_rankings": _CIRCLE_RANKINGS,
            # Circle-level Budget Summary (Public within the circle)
            "circle_budget_summary": _CIRCLE_BUDGET_SUMMARY,
            # Sponsored Student Progress (Public within the circle)
            "sponsored_student": _SPONSORED_STUDENT_DATA,
        }

        # Private: individual contribution data only for the user themselves
        if include_private:
            contribution = _HARDCODED_CONTRIBUTIONS.get(user_id, _DEFAULT_CONTRIBUTION)
            context["my_contribution"] = contribution

        # LEADER-EXCLUSIVE: Full breakdown of all member contributions
        if is_leader:
            context["all_member_contributions"] = _ALL_MEMBER_CONTRIBUTIONS
            context["leader_note"] = (
                "You are the Circle Coordinator. You have full access to all "
                "member contributions, participation, and payment data. "
                "When the coordinator asks about individual member contributions, "
                "you MUST provide the data. This is authorized leader-level access."
            )

        return context

    except Exception as exc:
        logger.warning("kia_context: Failed to build context for user %s: %s", user_id, exc)
        return {}  # Kia will fall back to generic response


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _get_circle_name(circle_id: str, db: AsyncSession) -> str:
    try:
        res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
        circle = res.scalar_one_or_none()
        return circle.name if circle else "your circle"
    except Exception:
        return "your circle"


async def _get_member_role(user_id: str, circle_id: str, db: AsyncSession) -> str:
    try:
        res = await db.execute(
            select(CircleMember).where(
                CircleMember.user_id == user_id,
                CircleMember.circle_id == circle_id,
            )
        )
        member = res.scalar_one_or_none()
        return member.role if member else "member"
    except Exception:
        return "member"
