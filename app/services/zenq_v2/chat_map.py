"""Map live RAS chat fields → ZenQ v2 CHAT_* codes (no LLM).

Worthy chats only: SUBST / ENCOUR / SHARE earn IP.
Low-effort / non-substantive messages return None (no CHAT_REACT emit).
"""

from __future__ import annotations

from typing import Optional


def map_chat_event(
    *,
    ras_score: float,
    substantive: bool,
    shield_action: str,
) -> Optional[str]:
    """Return CHAT_* code or None to skip emit (blocked / not worthy)."""
    action = (shield_action or "").strip().lower()
    if action in ("block", "blocked", "reject", "denied", "drop"):
        return None

    # One-liners / low-effort — do not write ledger noise or award IP
    if not substantive:
        return None

    ras = float(ras_score or 0)
    if ras >= 0.75:
        return "CHAT_SUBST"
    if ras >= 0.45:
        return "CHAT_ENCOUR"
    return "CHAT_SHARE"
