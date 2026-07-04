"""AI-backed RAS scoring for ZenQ chat messages (Groq + heuristics)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional

from app.algorithms.zenq.aggregators import is_substantive_message
from app.algorithms.zenq.ras import score_message_ras
from app.core.settings import settings

logger = logging.getLogger(__name__)

AI_BLEND_WEIGHT = 0.62
HEURISTIC_BLEND_WEIGHT = 0.38
_AI_TIMEOUT_SEC = 4.0
_GROQ_RAS_MODEL = "llama-3.1-8b-instant"

_RAS_SYSTEM_PROMPT = """You rate youth mentorship chat messages for ZENK Impact.

Score mentoring MESSAGE QUALITY for sponsor→student circles (not moderation — safety is handled separately).

Return JSON ONLY:
{
  "ras_score": <float 0.0-1.0>,
  "substantive": <true|false>,
  "student_centred": <true|false>,
  "actionable": <true|false>,
  "effort_band": "low"|"moderate"|"strong"|"excellent",
  "summary": "<max 12 words>"
}

Guidelines:
- 0.2-0.4: one-word, emoji-only, generic "ok/thanks", off-topic spam
- 0.45-0.65: polite but thin; little student-specific value
- 0.66-0.85: relevant encouragement, questions, or concrete support
- 0.86-1.0: specific plans, reflective guidance, clear student-centred action
- substantive=true when the message meaningfully advances mentorship (not just "hi")
- Penalize copy-paste tone, ALL CAPS rants, and vague platitudes
"""

_groq_client = None


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _parse_ai_json(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _get_groq_client():
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
        logger.warning("[ZenQ RAS] Groq SDK unavailable: %s", exc)
        return None


def _groq_ras_sync(snippet: str) -> Optional[str]:
    client = _get_groq_client()
    if not client:
        return None
    response = client.chat.completions.create(
        model=_GROQ_RAS_MODEL,
        messages=[
            {"role": "system", "content": _RAS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f'Rate this mentorship message:\n"""{snippet}"""',
            },
        ],
        temperature=0.1,
        max_tokens=220,
        response_format={"type": "json_object"},
    )
    if response.choices and response.choices[0].message.content:
        return response.choices[0].message.content.strip()
    return None


async def analyze_message_ras_ai(text: Optional[str]) -> Optional[dict[str, Any]]:
    if not text or not (text or "").strip():
        return None
    if not settings.zenq_ai_ras_enabled:
        return None
    if not settings.groq_api_key:
        return None

    snippet = (text or "").strip()[:2000]

    try:
        raw = await asyncio.wait_for(
            asyncio.to_thread(_groq_ras_sync, snippet),
            timeout=_AI_TIMEOUT_SEC,
        )
        parsed = _parse_ai_json(raw or "")
        if not parsed:
            return None
        ras = _clamp(float(parsed.get("ras_score", 0.5)))
        return {
            "ras_score": round(ras, 3),
            "substantive": bool(parsed.get("substantive")),
            "student_centred": bool(parsed.get("student_centred")),
            "actionable": bool(parsed.get("actionable")),
            "effort_band": str(parsed.get("effort_band") or "moderate"),
            "summary": str(parsed.get("summary") or "")[:120],
            "source": "groq",
            "model": _GROQ_RAS_MODEL,
        }
    except Exception as exc:
        logger.debug("[ZenQ RAS Groq] skipped: %s", exc)
        return None


def blend_ras_scores(
    heuristic_ras: float,
    ai_ras: Optional[float],
    *,
    shield_action: str = "allow",
) -> float:
    action = (shield_action or "allow").lower()
    if action == "block":
        return round(_clamp(min(heuristic_ras, 0.22)), 3)

    if ai_ras is None:
        return round(_clamp(heuristic_ras), 3)

    blended = HEURISTIC_BLEND_WEIGHT * heuristic_ras + AI_BLEND_WEIGHT * float(ai_ras)
    if action == "warn":
        blended -= 0.12
    return round(_clamp(blended), 3)


async def message_quality_fields_async(
    text: Optional[str],
    shield_action: str = "allow",
) -> dict[str, Any]:
    """Heuristic + optional Groq RAS; substantive from either layer."""
    heuristic_sub = is_substantive_message(text)
    heuristic_ras = score_message_ras(
        text,
        shield_action,
        substantive=heuristic_sub,
    )

    ai = await analyze_message_ras_ai(text)
    ai_ras = float(ai["ras_score"]) if ai else None
    final_ras = blend_ras_scores(heuristic_ras, ai_ras, shield_action=shield_action)

    substantive = heuristic_sub
    if ai and ai.get("substantive"):
        substantive = True
    if ai and ai.get("student_centred") and ai.get("actionable"):
        substantive = True

    ras_source = "heuristic"
    if ai_ras is not None:
        ras_source = "groq_blended" if ai and ai.get("source") == "groq" else "ai_blended"

    return {
        "ras_score": final_ras,
        "zenq_substantive": substantive,
        "ras_heuristic": round(heuristic_ras, 3),
        "ras_ai": ai_ras,
        "ras_source": ras_source,
        "ras_ai_summary": (ai or {}).get("summary"),
    }


def message_quality_fields(
    text: Optional[str],
    shield_action: str = "allow",
) -> dict[str, float | bool]:
    """Sync fallback — heuristics only (legacy callers)."""
    from app.algorithms.zenq.ras import message_quality_fields as _heuristic_fields

    base = _heuristic_fields(text, shield_action)
    return {
        "ras_score": base["ras_score"],
        "zenq_substantive": base["zenq_substantive"],
    }
