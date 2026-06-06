"""UTC datetime helpers for API responses."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """
    Serialize a UTC (or naive-UTC) datetime for JSON/JS.
    Appends 'Z' so browsers parse as UTC and toLocaleString() shows local time correctly.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat() + "Z"
