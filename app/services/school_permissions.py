"""School portal RBAC: roles, permission checks, and audit helpers."""
from __future__ import annotations

from typing import FrozenSet, Optional

ROLE_PRINCIPAL = "principal"
ROLE_STAFF = "staff"
VALID_ROLES = frozenset({ROLE_PRINCIPAL, ROLE_STAFF})

# Actions that change live data or external comms — principal only.
PRINCIPAL_ONLY: FrozenSet[str] = frozenset({
    "finalize_report",
    "finalize_kia_draft",
    "distribute_report",
    "notify_sl",
    "alert_sl_attendance",
    "download_all_reports",
    "manage_profile_photos",
    "view_audit_log",
    "manage_portal_access",
    "remove_student",
})

ALL_PERMISSIONS: FrozenSet[str] = frozenset({
    "view_dashboard",
    "submit_quarterly_report",
    "import_csv",
    "import_pdf",
    "approve_pdf_review",
    "reject_pdf_review",
    "manage_attendance",
    "request_meeting",
    "submit_enrollment",
    *PRINCIPAL_ONLY,
})

STAFF_PERMISSIONS: FrozenSet[str] = ALL_PERMISSIONS - PRINCIPAL_ONLY


def normalize_role(role: Optional[str]) -> str:
    r = (role or ROLE_PRINCIPAL).strip().lower()
    return r if r in VALID_ROLES else ROLE_PRINCIPAL


def permissions_for_role(role: Optional[str]) -> list[str]:
    r = normalize_role(role)
    perms = STAFF_PERMISSIONS if r == ROLE_STAFF else ALL_PERMISSIONS
    return sorted(perms)


def has_permission(role: Optional[str], permission: str) -> bool:
    return permission in permissions_for_role(role)
