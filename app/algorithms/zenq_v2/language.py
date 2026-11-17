"""Market / wall copy bans — Tech Guide CI language + Standalone claim tiers."""

from __future__ import annotations

from typing import Iterable, Optional

# Strings that must never appear in sponsor-facing ZenQ v2 market copy.
MARKET_LANGUAGE_BANS: list[str] = [
    "causal impact",
    "attributable impact",
    "proves impact",
    "caused by sponsorship",
    "SROI",
    "counterfactual proven",
]

WALL_LANGUAGE_BANS: list[str] = [
    "Do not show ZQA average as ZenQ",
    "Do not invent SESSION/TARGET from chat",
    "Do not show another circle's lifetime beside this one",
]

# Mandatory funder/sponsor claim strip (Phase 6) — pilot year framing.
FUNDER_CLAIM_LANGUAGE = (
    "Pilot year is judged on data completeness and comprehension — not impact claims."
)


def funder_claim_language() -> str:
    assert_copy_clean(FUNDER_CLAIM_LANGUAGE)
    return FUNDER_CLAIM_LANGUAGE


def banned_phrases_in_text(text: str, bans: Optional[Iterable[str]] = None) -> list[str]:
    """Return ban phrases found in text (case-insensitive)."""
    hay = (text or "").lower()
    out = []
    for phrase in bans or MARKET_LANGUAGE_BANS:
        if phrase.lower() in hay:
            out.append(phrase)
    return out


def assert_copy_clean(text: str, bans: Optional[Iterable[str]] = None) -> None:
    hits = banned_phrases_in_text(text, bans)
    if hits:
        raise AssertionError(f"banned market language: {hits}")


def market_language_ban_notes() -> list[str]:
    # Meta notes for UI/audit — must not themselves contain banned claim phrases.
    return [
        "CI language ban: no attribution claims on sponsor surfaces",
        "Do not show another circle's lifetime beside this one",
        "Ladder ranks season per member-month from the first scored circle",
        "Pilot: lifetime/PCS/ranks live from first circle and first member — no month seal",
    ]
