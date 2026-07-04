"""Response Authenticity Score (RAS) — heuristic message quality layer for ZenQ."""

from __future__ import annotations

import re
from typing import Optional

from .aggregators import is_substantive_message

_REPEATED_CHAR = re.compile(r"(.)\1{6,}")
_TOKEN_REPEAT = re.compile(r"\b(\w+)\b(?:\s+\1\b){3,}", re.IGNORECASE)
_EMOJI_HEAVY = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]{3,}"
)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def score_message_ras(
    text: Optional[str],
    shield_action: str = "allow",
    *,
    substantive: Optional[bool] = None,
) -> float:
    """
    Score 0–1 authenticity/effort for a single chat message.
    Deterministic — safe to run on every message at insert time.
    """
    cleaned = (text or "").strip()
    action = (shield_action or "allow").lower()

    if not cleaned:
        return 0.25

    score = 1.0

    if action == "warn":
        score -= 0.18
    elif action == "block":
        score = 0.20

    length = len(cleaned)
    if length < 6:
        score = min(score, 0.35)
    elif length < 14:
        score = min(score, 0.55)
    elif length < 25:
        score = min(score, 0.72)

    letters = [c for c in cleaned if c.isalpha()]
    if letters:
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio > 0.75 and length > 12:
            score -= 0.12

    if _REPEATED_CHAR.search(cleaned) or _TOKEN_REPEAT.search(cleaned):
        score -= 0.22

    if _EMOJI_HEAVY.fullmatch(cleaned.replace(" ", "")) or (
        len(cleaned) < 12 and _EMOJI_HEAVY.search(cleaned)
    ):
        score = min(score, 0.35)

    low_effort = {"ok", "k", "kk", "yes", "no", "hi", "hello", "thanks", "thank you", "gm", "gn"}
    if cleaned.lower().rstrip("!.") in low_effort:
        score = min(score, 0.50)

    is_sub = substantive if substantive is not None else is_substantive_message(cleaned)
    if is_sub and length >= 25:
        score += 0.08

    return round(_clamp(score), 3)


def message_quality_fields(
    text: Optional[str],
    shield_action: str = "allow",
) -> dict[str, float | bool]:
    substantive = is_substantive_message(text)
    return {
        "ras_score": score_message_ras(text, shield_action, substantive=substantive),
        "zenq_substantive": substantive,
    }
