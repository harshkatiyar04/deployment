"""Parse/store circle invite metadata on signup_requests.admin_note."""

from __future__ import annotations

LEADER_PENDING = "pending"
LEADER_APPROVED = "approved"
LEADER_REJECTED = "rejected"


def build_invite_note(circle_id: str, leader_status: str = LEADER_PENDING) -> str:
    cid = (circle_id or "").strip()
    status = (leader_status or LEADER_PENDING).strip().lower()
    return f"circle_invite={cid}|leader={status}"


def parse_invite_note(admin_note: str | None) -> tuple[str, str]:
    """Return (circle_id, leader_status)."""
    if not admin_note:
        return "", LEADER_PENDING
    circle_id = ""
    leader_status = LEADER_PENDING
    for part in admin_note.split("|"):
        part = part.strip()
        if part.startswith("circle_invite="):
            circle_id = part.split("=", 1)[1].strip()
        elif part.startswith("leader="):
            leader_status = part.split("=", 1)[1].strip().lower() or LEADER_PENDING
    if circle_id and "|" not in admin_note and "leader=" not in admin_note:
        if admin_note.startswith("circle_invite="):
            circle_id = admin_note.split("=", 1)[1].strip()
    return circle_id, leader_status


def merge_admin_kyc_note(existing: str | None, reviewer_note: str | None) -> str | None:
    """Preserve circle_invite|leader metadata when admin adds a review note."""
    note = (reviewer_note or "").strip()
    if not note:
        return existing
    circle_id, leader_status = parse_invite_note(existing)
    if circle_id:
        base = build_invite_note(circle_id, leader_status=leader_status)
        if f"review={note}" in (existing or ""):
            return existing
        return f"{base}|review={note}"
    return note


def invite_tag_for_query(circle_id: str) -> str:
    """Match legacy and new note formats for a circle."""
    return f"circle_invite={circle_id.strip()}"
