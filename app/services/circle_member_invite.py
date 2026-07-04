"""Parse/store circle invite metadata on signup_requests.admin_note."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

LEADER_PENDING = "pending"
LEADER_APPROVED = "approved"
LEADER_REJECTED = "rejected"

_INVITE_KEYS = frozenset({"circle_invite", "leader", "applied_at"})
_TZ_SUFFIX = re.compile(r"(Z|[+-]\d{2}:\d{2})$", re.I)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_applied_at_iso(value: str | None) -> str | None:
    """Ensure an applied_at string is parseable as UTC on the client."""
    at = (value or "").strip()
    if not at:
        return None
    if _TZ_SUFFIX.search(at):
        return at
    return f"{at}Z"


def recover_intended_utcnow(dt: datetime | None) -> datetime | None:
    """Recover intended UTC when ``datetime.utcnow()`` was written into TIMESTAMPTZ.

    On non-UTC DB sessions, naive utcnow is stored as local wall time, so the
    returned UTC instant is behind by the local offset (e.g. ~5.5h in India).
    Naive values are treated as UTC (driver already gave utcnow semantics).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    local_offset = datetime.now().astimezone().utcoffset() or timedelta(0)
    return dt.astimezone(timezone.utc) + local_offset


def application_applied_at_iso(
    admin_note: str | None,
    *,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> str | None:
    """UTC ISO for when the member applied via invite (not account signup alone)."""
    _, _, applied = parse_invite_note(admin_note)
    if applied:
        return normalize_applied_at_iso(applied)
    dt = updated_at or created_at
    recovered = recover_intended_utcnow(dt)
    if recovered is None:
        return None
    return recovered.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_invite_note(
    circle_id: str,
    leader_status: str = LEADER_PENDING,
    *,
    applied_at: str | None = None,
    existing_note: str | None = None,
) -> str:
    """Build invite metadata, preserving applied_at and non-invite note segments."""
    cid = (circle_id or "").strip()
    status = (leader_status or LEADER_PENDING).strip().lower()
    _, _, prev_applied = parse_invite_note(existing_note)
    at = normalize_applied_at_iso(applied_at or prev_applied) or _utc_now_iso()

    extras: list[str] = []
    if existing_note:
        for part in existing_note.split("|"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            key = part.split("=", 1)[0].strip()
            if key not in _INVITE_KEYS:
                extras.append(part)

    core = f"circle_invite={cid}|leader={status}|applied_at={at}"
    if extras:
        return f"{core}|{'|'.join(extras)}"
    return core


def parse_invite_note(admin_note: str | None) -> tuple[str, str, str | None]:
    """Return (circle_id, leader_status, applied_at)."""
    if not admin_note:
        return "", LEADER_PENDING, None
    circle_id = ""
    leader_status = LEADER_PENDING
    applied_at: str | None = None
    for part in admin_note.split("|"):
        part = part.strip()
        if part.startswith("circle_invite="):
            circle_id = part.split("=", 1)[1].strip()
        elif part.startswith("leader="):
            leader_status = part.split("=", 1)[1].strip().lower() or LEADER_PENDING
        elif part.startswith("applied_at="):
            applied_at = part.split("=", 1)[1].strip() or None
    if circle_id and "|" not in admin_note and "leader=" not in admin_note:
        if admin_note.startswith("circle_invite="):
            circle_id = admin_note.split("=", 1)[1].strip()
    return circle_id, leader_status, applied_at


def merge_admin_kyc_note(existing: str | None, reviewer_note: str | None) -> str | None:
    """Preserve circle_invite|leader|applied_at metadata when admin adds a review note."""
    note = (reviewer_note or "").strip()
    if not note:
        return existing
    circle_id, leader_status, applied_at = parse_invite_note(existing)
    if circle_id:
        base = build_invite_note(
            circle_id,
            leader_status=leader_status,
            applied_at=applied_at,
            existing_note=existing,
        )
        if f"review={note}" in (existing or ""):
            return existing
        return f"{base}|review={note}"
    return note


def invite_tag_for_query(circle_id: str) -> str:
    """Match legacy and new note formats for a circle."""
    return f"circle_invite={circle_id.strip()}"
