"""Helpers for admin KYC review notes and user-facing messages."""

from __future__ import annotations

from app.services.circle_member_invite import parse_invite_note


def extract_kyc_review_note(admin_note: str | None) -> str | None:
    """Return the reviewer comment shown to the applicant."""
    if not admin_note:
        return None
    for part in admin_note.split("|"):
        chunk = part.strip()
        if chunk.startswith("review="):
            text = chunk.split("=", 1)[1].strip()
            return text or None
    circle_id, _ = parse_invite_note(admin_note)
    if circle_id or admin_note.startswith("circle_invite="):
        return None
    text = admin_note.strip()
    return text or None
