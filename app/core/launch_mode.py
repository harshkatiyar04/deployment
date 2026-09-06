"""Soft-launch / waitlist helpers — Path 1 scaffold.

Default mode is ``full`` so existing signup and product APIs stay open until
``ZENK_LAUNCH_MODE=waitlist`` is set. Call sites that enforce waitlist must
opt in explicitly (none wired yet).
"""

from __future__ import annotations

from typing import Any

from app.core.settings import settings

LAUNCH_MODE_FULL = "full"
LAUNCH_MODE_WAITLIST = "waitlist"


def get_launch_mode() -> str:
    raw = (settings.launch_mode or LAUNCH_MODE_FULL).strip().lower()
    return LAUNCH_MODE_WAITLIST if raw == LAUNCH_MODE_WAITLIST else LAUNCH_MODE_FULL


def is_waitlist_launch() -> bool:
    return get_launch_mode() == LAUNCH_MODE_WAITLIST


def is_full_launch() -> bool:
    return not is_waitlist_launch()


def public_signup_enabled() -> bool:
    """KYC / circle signup APIs — off only in waitlist mode."""
    return is_full_launch()


def launch_config_payload() -> dict[str, Any]:
    mode = get_launch_mode()
    waitlist = mode == LAUNCH_MODE_WAITLIST
    return {
        "mode": mode,
        "public_signup_enabled": not waitlist,
        "circle_join_enabled": not waitlist,
        "interest_form_enabled": waitlist,
        "admin_login_enabled": True,
        "member_login_enabled": not waitlist,
    }
