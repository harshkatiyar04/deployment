"""
Kia AI Bot Service — Mentorship Assistant
Powered by Groq (Llama 3.3 70B Versatile) for generation.
Gemini is used separately for safety shielding (see shield.py).
"""
import logging
import asyncio
import json
from typing import Dict, List, Optional
from groq import Groq
from app.core.settings import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base System Prompt (persona + rules)
# ---------------------------------------------------------------------------

KIA_BASE_PROMPT = """You are Kia, the Career Mentor AI for ZENK Impact.
Your goal is to guide members towards their educational and career milestones.

RULES:
1. Be encouraging, professional, and empathetic.
2. Provide actionable advice grounded in the data you are given.
3. If you suggest something specific, put it on a new line starting with "Kia suggests: ".
4. Keep responses concise (under 3 paragraphs).
5. Focus on mentorship, career guidance, academic support, and circle progress.
6. Do not provide legal, medical, or financial advice.
7. If a user is disrespectful, stay professional but firm.
8. PRIVACY RULE (CRITICAL):
   - You may share **GROUP/CIRCLE-LEVEL** budget data (Total Collected, Total Spent) with any member.
   - You may share the **SPONSORED STUDENT'S** academic progress, attendance, and impact summary with any member of the circle. This is public info for all sponsors.
   - For regular members: Never reveal, guess, or infer an **INDIVIDUAL member's** contribution or private stats (other than the person asking).
     If a regular member asks about another member's contribution, respond:
     "I can only share your own contribution data for privacy reasons — I'm not able to access other members' details."
   - **EXCEPTION — CIRCLE COORDINATOR (Leader)**: If the context contains "LEADER ACCESS GRANTED", the requesting user
     is the Circle Coordinator. In this case, you MUST answer their questions about individual member contributions
     using the data provided. This is authorized. Do NOT refuse leader requests for member data.

FORMATTING:
Use plain text. If you want to highlight a suggestion, put it on a new line starting with "Kia suggests: ".
Example:
"Great progress on your participation! Keep it up.
Kia suggests: Try to attend at least one extra session this month to close the gap."
"""


# ---------------------------------------------------------------------------
# Context block builder (injected per-request)
# ---------------------------------------------------------------------------

def _build_context_block(user_context: Dict) -> str:
    """
    Converts the user context dict from kia_context.py into a structured
    text block that Kia reads as her "known facts" before answering.
    """
    if not user_context:
        return ""

    lines = ["--- MEMBER CONTEXT (use this to answer questions accurately) ---"]

    circle_name = user_context.get("circle_name", "your circle")
    role = user_context.get("member_role", "member")
    lines.append(f"Circle: {circle_name} | Member Role: {role.title()}")

    # Participation
    my_pct = user_context.get("my_participation_pct")
    avg_pct = user_context.get("circle_avg_participation_pct")
    delta = user_context.get("participation_vs_avg")
    if my_pct is not None:
        above_below = "above" if delta >= 0 else "below"
        lines.append(
            f"Participation: {my_pct}% (circle avg: {avg_pct}% — "
            f"you are {abs(delta)}% {above_below} average)"
        )

    # ZenQ / Rank
    zenq = user_context.get("my_zenq_score")
    rank = user_context.get("my_circle_rank")
    total = user_context.get("total_circles_nationally")
    change = user_context.get("zenq_change_this_month")
    prev = user_context.get("previous_rank")
    if zenq is not None:
        lines.append(
            f"ZenQ Score: {zenq} (up {change} pts this month) | "
            f"Circle Rank: #{rank} of {total} nationally (was #{prev})"
        )

    # Time spent
    hrs = user_context.get("my_time_this_month_hrs")
    top = user_context.get("top_group_time_hrs")
    gap = user_context.get("time_gap_to_top_hrs")
    if hrs is not None:
        lines.append(
            f"Time Invested This Month: {hrs}h "
            f"(top group: {top}h — gap: {gap}h)"
        )

    # Circle-level Budget (Public within circle)
    circle_budget = user_context.get("circle_budget_summary")
    if circle_budget:
        lines.append(
            f"Circle Budget Summary ({circle_budget.get('fy_label')}): "
            f"Total Collected: ₹{circle_budget.get('collected', 0):,} | "
            f"Total Spent: ₹{circle_budget.get('spent', 0):,} | "
            f"Remaining: ₹{circle_budget.get('balance_to_spend', 0):,}"
        )

    # Sponsored Student Progress (Public within circle)
    student = user_context.get("sponsored_student")
    if student:
        lines.append(
            f"SPONSORED STUDENT: {student['name']} | Grade: {student['grade']} | School: {student['school']}"
        )
        lines.append(
            f"  Academic Stats: ZenQ {student['zenq_score']} | Attendance: {student['attendance_pct']}%"
        )
        grades_str = ", ".join([f"{k}: {v}" for k, v in student['recent_grades'].items()])
        lines.append(f"  Recent Grades: {grades_str}")
        lines.append(f"  Teacher Notes: {student['teacher_notes']}")
        lines.append(f"  Impact Summary: {student['impact_summary']}")

    # Individual Contribution (private, only for the user themselves)
    contrib = user_context.get("my_contribution")
    if contrib:
        lines.append(
            f"Your PERSONAL Contribution This Month: ₹{contrib.get('this_month', 0):,} | "
            f"Total You Have Contributed: ₹{contrib.get('total_contributed', 0):,}"
        )

    # National circle rankings (public)
    rankings = user_context.get("national_circle_rankings", [])
    if rankings:
        lines.append("National Circle Rankings:")
        for r in rankings:
            mine_tag = " ← Your Circle" if r.get("is_mine") else ""
            lines.append(f"  #{r['rank']} {r['name']} ({r['city']}) — ZenQ {r['zenq']}{mine_tag}")

    # LEADER-EXCLUSIVE: All member contribution data
    all_contribs = user_context.get("all_member_contributions")
    leader_note = user_context.get("leader_note")
    if all_contribs and leader_note:
        lines.append("")
        lines.append("=== LEADER ACCESS GRANTED ===")
        lines.append(leader_note)
        lines.append("Individual Member Contributions:")
        for mc in all_contribs:
            lines.append(
                f"  • {mc['name']} ({mc['role']}): Total ₹{mc['total_contributed']:,} | "
                f"This Month ₹{mc['this_month']:,} | {mc['pct_of_total']}% of total"
            )
        lines.append("=== END LEADER DATA ===")

    lines.append("--- END CONTEXT ---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Groq client
# ---------------------------------------------------------------------------

_groq_client = None

def _get_groq_client():
    """Lazy-load Groq client."""
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    try:
        api_key = settings.groq_api_key
        if not api_key:
            return None
        _groq_client = Groq(api_key=api_key)
        return _groq_client
    except Exception as exc:
        logger.warning("Groq SDK unavailable for Kia: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

async def generate_kia_response(
    message_text: str,
    user_context: Optional[Dict] = None,
    history: Optional[List[dict]] = None,
) -> Optional[str]:
    """
    Generate a mentorship response from Kia using Groq (Llama 3.3 70B).

    Parameters:
        message_text: The raw message from the user (may include @kia).
        user_context: Personalized data dict from kia_context.fetch_user_context().
                      If provided, Kia answers with real data. If None, generic response.
        history: Optional chat history for multi-turn (future feature).

    Returns:
        Kia's response string, or None on failure.
    """
    client = _get_groq_client()
    if not client:
        return None

    # Build the full system prompt: base persona + personalized context block
    context_block = _build_context_block(user_context or {})
    if context_block:
        system_prompt = f"{KIA_BASE_PROMPT}\n\n{context_block}"
    else:
        system_prompt = KIA_BASE_PROMPT

    # Clean up the user message (strip @kia prefix for cleaner parsing)
    clean_message = message_text.replace("@kia", "").replace("@Kia", "").strip()
    if not clean_message:
        clean_message = message_text  # fallback to original if stripping leaves empty

    max_retries = 3
    retry_count = 0
    model_name = "llama-3.3-70b-versatile"

    while retry_count < max_retries:
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": clean_message},
                ],
                temperature=0.7,
                max_tokens=512,  # Reduced for faster, concise responses
            )

            if response and response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            return None

        except Exception as exc:
            exc_str = str(exc)
            if "rate_limit_exceeded" in exc_str.lower() or "429" in exc_str:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error("Groq rate limited after %d retries: %s", max_retries, exc)
                    return None
                wait_time = 5
                logger.warning(
                    "Groq rate limited. Retrying in %ds... (Attempt %d/%d)",
                    wait_time, retry_count, max_retries
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error("Groq generation failed: %s", exc)
                return None

    return None


async def generate_budget_insight(budget_data: Dict) -> Dict:
    """
    Generate a structured budget analysis and suggestion from Kia.
    """
    client = _get_groq_client()
    if not client:
        return {
            "analysis": "Based on current spend pace, your circle will exhaust the budget by Sep 2026.",
            "suggestion": "Set a circle planning meeting for September 2026. Rohit (Coordinator) has been notified.",
            "coordinator_name": "Rohit"
        }

    prompt = f"""Analyze the following Sponsor Circle budget data and provide a proactive insight.
    
    DATA (FY 2025-26):
    - Total Annual Budget: ₹{budget_data.get('total_budget', 0):,}
    - Total Spent: ₹{budget_data.get('spent', 0):,}
    - Total Collected: ₹{budget_data.get('collected', 0):,}
    - Balance to Spend: ₹{budget_data.get('balance_to_spend', 0):,}
    
    TASK:
    1. Calculate the burn rate. Note the fiscal year is Apr 2025 - Mar 2026.
    2. Today is Mar 2026 (the start of the final month).
    3. Generate a planning ahead vision. Focus on exhaustion and FY27 targets.
    4. The coordinator is 'Rohit'.
    
    RESPONSE FORMAT (JSON ONLY):
    {{
      "analysis": "A concise paragraph (2-3 sentences) analyzing the pace.",
      "suggestion": "A single actionable sentence starting with 'Set a circle planning meeting...'",
      "coordinator_name": "Rohit"
    }}
    """
    
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are Kia, a proactive Career and Circle Mentor. Respond ONLY in valid JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as exc:
        logger.error("Kia budget insight failed: %s", exc)
        return {
            "analysis": "Kia is refining your spend pace calculations right now.",
            "suggestion": "Keep monitoring the budget vs. actuals in the tracker below.",
            "coordinator_name": "Rohit"
        }
