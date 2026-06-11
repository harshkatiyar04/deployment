"""Short-lived in-memory cache for heavy admin overview aggregates."""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_DASHBOARD_KEY = "admin_dashboard_overview_v1"
_DEFAULT_TTL_SECONDS = 45


def get_cached_dashboard_overview(
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> dict[str, Any] | None:
    row = _CACHE.get(_DASHBOARD_KEY)
    if not row:
        return None
    cached_at, payload = row
    if time.monotonic() - cached_at > ttl_seconds:
        _CACHE.pop(_DASHBOARD_KEY, None)
        return None
    return payload


def set_cached_dashboard_overview(payload: dict[str, Any]) -> None:
    _CACHE[_DASHBOARD_KEY] = (time.monotonic(), payload)


async def build_and_cache_dashboard_overview(
    db: AsyncSession,
    builder: Callable[[AsyncSession], Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    payload = await builder(db)
    set_cached_dashboard_overview(payload)
    return payload
