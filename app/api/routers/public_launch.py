"""Public launch-mode config — soft-launch / waitlist Path 1 scaffold."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.launch_mode import launch_config_payload

router = APIRouter(prefix="/public", tags=["public-launch"])


@router.get("/launch-config")
async def get_launch_config() -> dict[str, Any]:
    """Read-only launch gates for the website (no auth).

    Does not change signup behaviour by itself — enforcers opt in later.
    """
    return launch_config_payload()
