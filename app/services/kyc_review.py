"""Helpers for admin KYC review notes and user-facing messages."""

from __future__ import annotations

from app.services.circle_member_invite import parse_invite_note

_INTERNAL_NOTE_KEYS = frozenset({
    "member_kind",
    "linked_student",
    "role_label",
    "leader_status",
})


def _is_internal_metadata_part(part: str) -> bool:
    chunk = part.strip()
    if not chunk:
        return True
    if chunk.startswith("circle_invite="):
        return True
    if "=" not in chunk:
        return False
    key = chunk.split("=", 1)[0].strip().lower()
    return key in _INTERNAL_NOTE_KEYS


def extract_kyc_review_note(admin_note: str | None) -> str | None:
    """Return the reviewer comment shown to the applicant."""
    if not admin_note:
        return None
    review_notes: list[str] = []
    human_notes: list[str] = []
    for part in admin_note.split("|"):
        chunk = part.strip()
        if not chunk:
            continue
        if chunk.startswith("review="):
            text = chunk.split("=", 1)[1].strip()
            if text:
                review_notes.append(text)
            continue
        if _is_internal_metadata_part(chunk):
            continue
        human_notes.append(chunk)
    if review_notes:
        return review_notes[-1]
    circle_id, _ = parse_invite_note(admin_note)
    if circle_id or admin_note.startswith("circle_invite="):
        return None
    if human_notes:
        return " ".join(human_notes)
    return None
