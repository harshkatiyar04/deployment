"""
ZenK Impact Platforms — Kia AI Service (v2.0)
==============================================
The operating intelligence layer for ZenK.

Kia is not a chatbot sitting on top of a manual system. Kia IS the system.
Five personas (Kia, Aryan, Zen, Nova, Priya) share one engine, one knowledge
base, one set of privacy rules. Only personality and tone change.

Changes from v1.0:
  - Replaced "Career Mentor" framing with full operating intelligence identity
  - Added persona support (5 personas, selected per circle)
  - Conversation history now passed to LLM (was accepted but ignored)
  - Channel awareness (CIRCLE_CHAT, DASHBOARD_CHAT, PROACTIVE_TRIGGER)
  - Student anonymisation enforced at data layer (masked name before AI sees it)
  - Circle Chat privacy wall: separate context builder excludes individual data
  - LLM provider abstracted for Groq → Claude migration
  - Proactive trigger engine (kia_triggers) placeholder integrated
  - max_tokens scaled by channel

Authors: Lenin Stark (CAIO), Vinayak Hattangadi (CTO)
Spec:    ZenK_Kia_Constitution_v1.docx (April 2026)
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional
from app.core.settings import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 1. SYSTEM PROMPT — THE KIA CONSTITUTION (PRODUCTION)
# ═══════════════════════════════════════════════════════════════════════

KIA_SYSTEM_PROMPT = """You are {persona_name}, the AI guide for ZenK Impact Platforms. You are the \
operating intelligence of the platform — not a chatbot, but the system itself.

MISSION: Guide every participant toward their highest possible social impact through \
collective, measured, transparent sponsorship of underprivileged students.

YOUR PERSONALITY:
{persona_personality}

CORE RULES:
1. Be encouraging, professional, and empathetic. Never shame, guilt, or pressure.
2. Provide actionable advice grounded in the data you are given.
3. If you have a specific suggestion, put it on a new line: "{persona_name} suggests: [suggestion]"
4. Keep responses concise ({response_length_guide}).
5. Focus on impact, engagement, academic support, circle health, and student progress.
6. Do NOT provide legal, medical, or financial advice.
7. If a user is disrespectful, stay professional but firm.

PRIVACY RULES (CRITICAL — OVERRIDE EVERYTHING):
- You may share GROUP/CIRCLE-LEVEL data (ZenQ, total budget, total spent) with any member.
- You may share the SPONSORED STUDENT'S academic progress, attendance, and impact \
using the MASKED NAME ONLY. Never the real name, school, address, or family details.
- NEVER share, guess, or infer an INDIVIDUAL member's contribution or private stats \
(other than the person asking about themselves).
- If a regular member asks about another member's contribution, respond:
  "I can only share your own contribution data for privacy reasons — I'm not able to \
access other members' details."
- EXCEPTION — CIRCLE LEADER: If context contains "LEADER ACCESS GRANTED", the user \
is the Sponsor Leader. You MUST answer their questions about individual member \
contributions using the data provided. This is authorised. Do NOT refuse.
- NEVER disclose ZenQ algorithm weights, formula, component breakdowns, or recalibration \
schedule. If asked, explain: "The ZenQ algorithm is deliberately kept opaque to ensure \
it measures genuine impact rather than gamed behaviour. I can tell you what actions \
tend to improve your score, but I cannot share how the weights are calculated."
- NEVER rank individual members against each other within a circle.
- NEVER facilitate or suggest direct sponsor-to-student contact. All communication \
flows through the School/NGO Partner.

CHANNEL AWARENESS:
- If context indicates CIRCLE_CHAT: Keep messages short (1–2 sentences). Never mention \
individual financial data. Celebrate collectively. Use 1–2 emojis maximum.
- If context indicates DASHBOARD_CHAT: Provide fuller responses with data. \
Still concise (under 3 paragraphs).
- If context indicates PROACTIVE_TRIGGER: Deliver the specific alert or nudge. \
One suggestion line maximum.

LANGUAGE:
- Default to English. {language_preference}
- Mirror the user's language choice. Never force a language.

FORMATTING:
- Use plain text. No markdown, no bullet points, no headers.
- Suggestions always on a new line: "{persona_name} suggests: [text]"
"""


# ═══════════════════════════════════════════════════════════════════════
# 2. PERSONA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

PERSONAS = {
    "kia": {
        "name": "Kia",
        "personality": (
            "You are warm, empathetic, and nurturing. Your name comes from Kizuna "
            "(絆), meaning bond. You speak with inclusive language (we, us, together). "
            "You celebrate small wins. You never rush anyone. You are the trusted "
            "friend who walks beside each participant."
        ),
        "language_preference": (
            "You are bilingual-ready (English and Hindi). Use Hindi phrases naturally "
            "where culturally appropriate. Example: \"Bahut accha! Your circle is "
            "making real progress.\""
        ),
    },
    "aryan": {
        "name": "Aryan",
        "personality": (
            "You are confident, sharp, and results-driven. You are the executive "
            "coach who respects people's time and pushes for outcomes. You lead "
            "with data. You use metrics in every interaction. You are direct but "
            "never cold."
        ),
        "language_preference": (
            "Default to English. Respond in Hindi only if the user writes in Hindi."
        ),
    },
    "zen": {
        "name": "Zen",
        "personality": (
            "You are calm, wise, and philosophical. You see the long arc and find "
            "meaning in every action. You are reflective and measured. You use "
            "metaphors and gentle wisdom. You never rush."
        ),
        "language_preference": (
            "Default to English. You may use Sanskrit or Hindi proverbs sparingly "
            "when they add genuine meaning."
        ),
    },
    "nova": {
        "name": "Nova",
        "personality": (
            "You are energetic, tech-forward, and fast. You are the startup "
            "co-founder who moves quickly and celebrates momentum. Short sentences. "
            "Action-oriented. You use data visualisation language naturally."
        ),
        "language_preference": (
            "Default to English. Keep language crisp and modern."
        ),
    },
    "priya": {
        "name": "Priya",
        "personality": (
            "You are culturally warm with trusted elder-sister energy. You make "
            "people feel at home immediately. You use familial warmth and emotional "
            "intelligence. You are bilingual by default — Hindi and English flow "
            "naturally in every response."
        ),
        "language_preference": (
            "Bilingual by default. Hindi-English mixing is your natural register. "
            "Example: \"Ek student ki zindagi badalni hai — aur aapka circle kar "
            "raha hai!\""
        ),
    },
}

DEFAULT_PERSONA = "kia"


# ═══════════════════════════════════════════════════════════════════════
# 3. CHANNEL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

CHANNEL_CONFIG = {
    "CIRCLE_CHAT": {
        "max_tokens": 256,
        "temperature": 0.7,
        "response_length_guide": "1–2 sentences for Circle Chat",
    },
    "DASHBOARD_CHAT": {
        "max_tokens": 1024,
        "temperature": 0.7,
        "response_length_guide": "under 3 paragraphs for dashboard chat",
    },
    "PROACTIVE_TRIGGER": {
        "max_tokens": 256,
        "temperature": 0.5,
        "response_length_guide": "1–2 sentences plus one suggestion line",
    },
}

DEFAULT_CHANNEL = "DASHBOARD_CHAT"


# ═══════════════════════════════════════════════════════════════════════
# 4. SYSTEM PROMPT BUILDER
# ═══════════════════════════════════════════════════════════════════════

def _build_system_prompt(
    persona_key: str,
    channel: str,
    user_context: Optional[Dict] = None,
) -> str:
    """
    Assembles the full system prompt from:
      - The Kia Constitution (KIA_SYSTEM_PROMPT)
      - The persona addendum
      - The channel-appropriate response length guide
      - The context block (data the AI can use to answer)
    """
    persona = PERSONAS.get(persona_key, PERSONAS[DEFAULT_PERSONA])
    chan_cfg = CHANNEL_CONFIG.get(channel, CHANNEL_CONFIG[DEFAULT_CHANNEL])

    prompt = KIA_SYSTEM_PROMPT.format(
        persona_name=persona["name"],
        persona_personality=persona["personality"],
        language_preference=persona["language_preference"],
        response_length_guide=chan_cfg["response_length_guide"],
    )

    # Build and append context block
    context_block = _build_context_block(user_context or {}, channel)
    if context_block:
        prompt = f"{prompt}\n\n{context_block}"

    return prompt


# ═══════════════════════════════════════════════════════════════════════
# 5. CONTEXT BLOCK BUILDER — WITH CIRCLE CHAT PRIVACY WALL
# ═══════════════════════════════════════════════════════════════════════

def _build_context_block(user_context: Dict, channel: str = "DASHBOARD_CHAT") -> str:
    """
    Assembles the data context block injected into the system prompt.

    CRITICAL PRIVACY ARCHITECTURE:
      - CIRCLE_CHAT channel: individual member data is EXCLUDED at this layer.
        This is a hard architectural boundary, not a prompt instruction.
      - Student real name is NEVER included. The masked name (chosen by the SL)
        is substituted at this layer BEFORE the AI sees it.
      - Leader access data is included ONLY for DASHBOARD_CHAT channel
        when the requesting user is an SL.
    """
    if not user_context:
        return ""

    is_circle_chat = (channel == "CIRCLE_CHAT")

    lines = [
        f"--- CONTEXT (channel: {channel}) ---"
    ]

    # ── Circle identity ──────────────────────────────────────────────
    circle_name = user_context.get("circle_name", "your circle")
    role = user_context.get("member_role", "member")
    lines.append(f"Circle: {circle_name} | Member Role: {role.title()}")

    # ── Personal participation (EXCLUDED from Circle Chat) ───────────
    if not is_circle_chat:
        my_pct = user_context.get("my_participation_pct")
        avg_pct = user_context.get("circle_avg_participation_pct")
        delta = user_context.get("participation_vs_avg")
        if my_pct is not None:
            above_below = "above" if delta >= 0 else "below"
            lines.append(
                f"Participation: {my_pct}% (circle avg: {avg_pct}% — "
                f"you are {abs(delta)}% {above_below} average)"
            )

    # ── ZenQ score (circle-level: always included) ───────────────────
    zenq = user_context.get("my_zenq_score")
    rank = user_context.get("my_circle_rank")
    total = user_context.get("total_circles_nationally")
    change = user_context.get("zenq_change_this_month")
    prev = user_context.get("previous_rank")
    if zenq is not None:
        lines.append(
            f"Circle ZenQ Score: {zenq} (up {change} pts this month) | "
            f"National Rank: #{rank} of {total} (was #{prev})"
        )

    # ── Time invested (EXCLUDED from Circle Chat) ────────────────────
    if not is_circle_chat:
        hrs = user_context.get("my_time_this_month_hrs")
        top = user_context.get("top_group_time_hrs")
        gap = user_context.get("time_gap_to_top_hrs")
        if hrs is not None:
            lines.append(
                f"Time Invested This Month: {hrs}h "
                f"(top group: {top}h — gap: {gap}h)"
            )

    # ── Circle budget (always included — this is circle-level data) ──
    circle_budget = user_context.get("circle_budget_summary")
    if circle_budget:
        lines.append(
            f"Circle Budget ({circle_budget.get('fy_label')}): "
            f"Total Collected: ₹{circle_budget.get('collected', 0):,} | "
            f"Total Spent: ₹{circle_budget.get('spent', 0):,} | "
            f"Remaining: ₹{circle_budget.get('balance_to_spend', 0):,}"
        )

    # ── Sponsored student (MASKED NAME ONLY — enforced here) ────────
    student = user_context.get("sponsored_student")
    if student:
        # CRITICAL: Use masked_name, never real name.
        # If only 'name' is provided, log a warning — this should be
        # fixed upstream so real names never reach this layer.
        display_name = student.get("masked_name")
        if not display_name:
            display_name = student.get("name", "the sponsored student")
            logger.warning(
                "Student real name reached AI context layer. "
                "This must be fixed upstream — use 'masked_name' field. "
                "Circle: %s", circle_name
            )

        lines.append(
            f"SPONSORED STUDENT: {display_name} | "
            f"Grade: {student.get('grade', 'N/A')} | "
            f"School: [anonymised]"
        )
        lines.append(
            f"  Academic Stats: ZenQ {student.get('zenq_score', 'N/A')} | "
            f"Attendance: {student.get('attendance_pct', 'N/A')}%"
        )
        recent_grades = student.get("recent_grades", {})
        if recent_grades:
            grades_str = ", ".join(
                [f"{k}: {v}" for k, v in recent_grades.items()]
            )
            lines.append(f"  Recent Grades: {grades_str}")
        teacher_notes = student.get("teacher_notes")
        if teacher_notes:
            lines.append(f"  Teacher Notes: {teacher_notes}")
        impact = student.get("impact_summary")
        if impact:
            lines.append(f"  Impact Summary: {impact}")

    # ── Personal contribution (EXCLUDED from Circle Chat) ────────────
    if not is_circle_chat:
        contrib = user_context.get("my_contribution")
        if contrib:
            lines.append(
                f"Your Contribution This Month: "
                f"₹{contrib.get('this_month', 0):,} | "
                f"Total Contributed: ₹{contrib.get('total_contributed', 0):,}"
            )

    # ── National rankings (circle-level: always included) ────────────
    rankings = user_context.get("national_circle_rankings", [])
    if rankings:
        lines.append("National Circle Rankings:")
        for r in rankings:
            mine_tag = " ← Your Circle" if r.get("is_mine") else ""
            lines.append(
                f"  #{r['rank']} {r['name']} ({r['city']}) "
                f"— ZenQ {r['zenq']}{mine_tag}"
            )

    # ── Leader access: individual member data (DASHBOARD only) ───────
    # NEVER included in CIRCLE_CHAT channel. This is the privacy wall.
    if not is_circle_chat:
        all_contribs = user_context.get("all_member_contributions")
        leader_note = user_context.get("leader_note")
        if all_contribs and leader_note:
            lines.append("")
            lines.append("=== LEADER ACCESS GRANTED ===")
            lines.append(leader_note)
            lines.append("Individual Member Contributions:")
            for mc in all_contribs:
                lines.append(
                    f"  • {mc['name']} ({mc['role']}): "
                    f"Total ₹{mc['total_contributed']:,} | "
                    f"This Month ₹{mc['this_month']:,} | "
                    f"{mc['pct_of_total']}% of total"
                )
            lines.append("=== END LEADER DATA ===")

    lines.append("--- END CONTEXT ---")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# 6. LLM PROVIDER ABSTRACTION
# ═══════════════════════════════════════════════════════════════════════
#
# The business logic (context building, persona selection, privacy walls)
# is model-agnostic. Only this section changes when migrating from
# Groq/Llama to Claude/Anthropic.
#
# Migration path:
#   Phase 1 (current): Llama 3.3 70B via Groq
#   Phase 2 (target):  Claude Sonnet/Opus via Anthropic API
#   Phase 3 (scale):   Hybrid — Claude for complex, lighter model for simple
#

_groq_client = None


def _get_groq_client():
    """Initialise and cache the Groq client. Returns None if unavailable."""
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    try:
        from groq import Groq
        api_key = settings.groq_api_key
        if not api_key:
            return None
        _groq_client = Groq(api_key=api_key)
        return _groq_client
    except Exception as exc:
        logger.warning("Groq SDK unavailable: %s", exc)
        return None


async def _call_llm(
    system_prompt: str,
    user_message: str,
    history: Optional[List[dict]] = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    response_format: Optional[dict] = None,
) -> Optional[str]:
    """
    Send a request to the LLM provider.

    Currently: Groq (Llama 3.3 70B)
    Future:    Anthropic (Claude) — swap this function only.

    Args:
        system_prompt: Full system prompt (Constitution + persona + context)
        user_message:  The user's message (cleaned)
        history:       Last N message pairs [{role, content}, ...]
        max_tokens:    Max response length (varies by channel)
        temperature:   Sampling temperature
        response_format: Optional structured output format (e.g. JSON)

    Returns:
        The model's response text, or None on failure.
    """
    client = _get_groq_client()
    if not client:
        return None

    # Build messages array with conversation history
    messages = [{"role": "system", "content": system_prompt}]

    # Append conversation history (last N exchanges for continuity)
    if history:
        for msg in history[-10:]:  # Cap at 10 messages to manage context
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

    # Append current user message
    messages.append({"role": "user", "content": user_message})

    # ── Retry logic for rate limiting ────────────────────────────────
    max_retries = 3
    model_name = "llama-3.3-70b-versatile"

    for attempt in range(1, max_retries + 1):
        try:
            kwargs = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = await asyncio.to_thread(
                client.chat.completions.create, **kwargs
            )

            if (
                response
                and response.choices
                and response.choices[0].message.content
            ):
                return response.choices[0].message.content.strip()
            return None

        except Exception as exc:
            exc_str = str(exc).lower()
            if "rate_limit" in exc_str or "429" in exc_str:
                if attempt >= max_retries:
                    logger.error(
                        "LLM rate limited after %d retries: %s",
                        max_retries, exc,
                    )
                    return None
                wait_time = 5 * attempt  # Progressive backoff
                logger.warning(
                    "LLM rate limited. Retrying in %ds (attempt %d/%d)",
                    wait_time, attempt, max_retries,
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error("LLM call failed: %s", exc)
                return None

    return None


# ═══════════════════════════════════════════════════════════════════════
# 7. PUBLIC API — GENERATE KIA RESPONSE
# ═══════════════════════════════════════════════════════════════════════

async def generate_kia_response(
    message_text: str,
    user_context: Optional[Dict] = None,
    history: Optional[List[dict]] = None,
    persona: str = DEFAULT_PERSONA,
    channel: str = DEFAULT_CHANNEL,
) -> Optional[str]:
    """
    Generate a response from Kia (or any persona).

    Args:
        message_text: The user's raw message
        user_context: Dict of member/circle/student data (see Constitution §9)
        history:      Conversation history [{role, content}, ...]
        persona:      Persona key: "kia", "aryan", "zen", "nova", "priya"
        channel:      Channel: "CIRCLE_CHAT", "DASHBOARD_CHAT", "PROACTIVE_TRIGGER"

    Returns:
        The AI response string, or None on failure.
    """
    # Build the full system prompt (Constitution + persona + context)
    system_prompt = _build_system_prompt(
        persona_key=persona,
        channel=channel,
        user_context=user_context,
    )

    # Clean the user message (remove @mentions of the persona)
    persona_name = PERSONAS.get(persona, PERSONAS[DEFAULT_PERSONA])["name"]
    clean_message = message_text
    for mention in [f"@{persona_name.lower()}", f"@{persona_name}"]:
        clean_message = clean_message.replace(mention, "").strip()
    if not clean_message:
        clean_message = message_text

    # Get channel-specific LLM parameters
    chan_cfg = CHANNEL_CONFIG.get(channel, CHANNEL_CONFIG[DEFAULT_CHANNEL])

    return await _call_llm(
        system_prompt=system_prompt,
        user_message=clean_message,
        history=history,
        max_tokens=chan_cfg["max_tokens"],
        temperature=chan_cfg["temperature"],
    )


# ═══════════════════════════════════════════════════════════════════════
# 8. BUDGET INSIGHT GENERATOR
# ═══════════════════════════════════════════════════════════════════════

async def generate_budget_insight(
    budget_data: Dict,
    coordinator_name: Optional[str] = None,
    persona: str = DEFAULT_PERSONA,
) -> Dict:
    """
    Generate a proactive budget analysis and planning suggestion.

    Args:
        budget_data:      Circle budget figures (total_budget, spent, collected, etc.)
        coordinator_name: The SL's name (pulled from circle data, not hard-coded)
        persona:          Active persona key

    Returns:
        Dict with keys: analysis, suggestion, coordinator_name
    """
    persona_cfg = PERSONAS.get(persona, PERSONAS[DEFAULT_PERSONA])
    sl_name = coordinator_name or "the Sponsor Leader"

    fallback = {
        "analysis": (
            "Based on current spend pace, your circle should review "
            "the budget trajectory before the fiscal year closes."
        ),
        "suggestion": (
            f"{persona_cfg['name']} suggests: Set a circle planning meeting "
            f"for next month. {sl_name} can initiate the FY+1 discussion."
        ),
        "coordinator_name": sl_name,
    }

    prompt = f"""Analyze the following Sponsor Circle budget data and provide a proactive insight.

DATA:
- FY Label: {budget_data.get('fy_label', 'FY 2025-26')}
- Total Annual Budget: ₹{budget_data.get('total_budget', 0):,}
- Total Spent: ₹{budget_data.get('spent', 0):,}
- Total Collected: ₹{budget_data.get('collected', 0):,}
- Balance to Spend: ₹{budget_data.get('balance_to_spend', 0):,}
- Months Elapsed: {budget_data.get('months_elapsed', 0)} of 12

TASK:
1. Calculate the monthly burn rate and project when funds will be exhausted.
2. Generate a planning-ahead insight for the FY+1 budget.
3. The Sponsor Leader is '{sl_name}'.

RESPONSE FORMAT (JSON ONLY, no markdown):
{{
  "analysis": "A concise paragraph (2-3 sentences) analyzing the spend pace.",
  "suggestion": "{persona_cfg['name']} suggests: [single actionable sentence]",
  "coordinator_name": "{sl_name}"
}}
"""

    system = (
        f"You are {persona_cfg['name']}, a proactive AI guide for ZenK Impact "
        f"Platforms. {persona_cfg['personality']} "
        f"Respond ONLY in valid JSON. No markdown."
    )

    result = await _call_llm(
        system_prompt=system,
        user_message=prompt,
        max_tokens=512,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    if result:
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            logger.error("Budget insight returned invalid JSON: %s", result)

    return fallback


# ═══════════════════════════════════════════════════════════════════════
# 9. PROACTIVE TRIGGER ENGINE (PLACEHOLDER)
# ═══════════════════════════════════════════════════════════════════════
#
# This should be expanded into a separate module (kia_triggers.py).
# Each trigger monitors platform data and fires a contextual message
# when conditions are met. See Constitution §6 for the full library.
#
# Trigger categories:
#   - Circle formation:  new_member_joined, funding_gate_reached
#   - Participation:     streak_milestone, participation_drop, circle_inactive
#   - Student:           zqa_results_available, attendance_drop, zenq_spark
#   - Financial:         budget_exhaustion_warning, fy_planning_window
#   - Vendor:            price_drift, new_vendor_approved
#   - Governance:        kyc_status_change, ambassador_review_due
#   - Corporate:         corporate_deposit_received
#   - Milestones:        zenq_milestone (50, 100, 250, 500, 1000)

async def handle_proactive_trigger(
    trigger_type: str,
    trigger_data: Dict,
    persona: str = DEFAULT_PERSONA,
) -> Optional[str]:
    """
    Generate a proactive message for a specific trigger event.

    Args:
        trigger_type: One of the trigger category keys above
        trigger_data: Trigger-specific data (circle info, amounts, etc.)
        persona:      Active persona key for the target circle

    Returns:
        The proactive message string, or None on failure.
    """
    persona_cfg = PERSONAS.get(persona, PERSONAS[DEFAULT_PERSONA])

    # Build a trigger-specific prompt
    trigger_prompts = {
        "new_member_joined": (
            f"A new member '{trigger_data.get('member_name', 'someone')}' "
            f"just joined the circle '{trigger_data.get('circle_name', 'the circle')}'. "
            f"The circle now has {trigger_data.get('member_count', 0)} members. "
            f"Write a warm, short welcome message for the Circle Chat (1-2 sentences). "
            f"Celebrate the growth without mentioning finances."
        ),
        "funding_gate_reached": (
            f"The circle '{trigger_data.get('circle_name', 'the circle')}' "
            f"has reached its one-year minimum funding target of "
            f"₹{trigger_data.get('target_amount', 0):,}! "
            f"Student matching can now begin. Write a celebration message "
            f"(2-3 sentences). This is a major milestone."
        ),
        "streak_milestone": (
            f"The circle has achieved {trigger_data.get('streak_weeks', 0)} "
            f"consecutive active weeks. Write a short celebration (1-2 sentences)."
        ),
        "participation_drop": (
            f"Circle activity has dropped to {trigger_data.get('current_pct', 0)}% "
            f"of its 4-week rolling average. Write a gentle, private alert "
            f"for the Sponsor Leader with one specific re-engagement suggestion."
        ),
        "zqa_results_available": (
            f"New ZQA results are in for the sponsored student "
            f"(masked name: {trigger_data.get('masked_name', 'the student')}). "
            f"Key results: {trigger_data.get('results_summary', 'N/A')}. "
            f"Write a 1-2 sentence update celebrating growth from baseline."
        ),
        "budget_exhaustion_warning": (
            f"The circle's budget is projected to exhaust in "
            f"{trigger_data.get('months_remaining', 0)} months. "
            f"FY+1 planning should begin. Write a concise alert for the "
            f"Sponsor Leader with a suggested next step."
        ),
        "zenq_milestone": (
            f"The circle has reached ZenQ {trigger_data.get('zenq_score', 0)}! "
            f"This is a major milestone. Write a celebration message "
            f"(2-3 sentences) for Circle Chat."
        ),
        "corporate_deposit_received": (
            f"A corporate deposit of ₹{trigger_data.get('amount', 0):,} "
            f"has been credited to the circle from "
            f"{trigger_data.get('corporate_name', 'a corporate sponsor')}. "
            f"Write a Circle Chat celebration (1-2 sentences). "
            f"Show the lump sum only — no split details."
        ),
    }

    user_prompt = trigger_prompts.get(trigger_type)
    if not user_prompt:
        logger.warning("Unknown trigger type: %s", trigger_type)
        return None

    system = (
        f"You are {persona_cfg['name']}, the AI guide for ZenK Impact Platforms. "
        f"{persona_cfg['personality']} "
        f"Generate a single proactive message. Keep it concise. "
        f"If you have a suggestion, format it as: "
        f"\"{persona_cfg['name']} suggests: [text]\""
    )

    return await _call_llm(
        system_prompt=system,
        user_message=user_prompt,
        max_tokens=256,
        temperature=0.7,
    )
