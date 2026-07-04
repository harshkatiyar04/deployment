"""Impact decay helpers (Phase 4)."""

from __future__ import annotations

from datetime import datetime, timezone

from .core import apply_decay


def months_since(dt: datetime | None, now: datetime | None = None) -> int:
    if not dt:
        return 99
    now = now or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta_days = max(0, (now - dt).days)
    return delta_days // 30


def apply_zeq_decay(zeq: float, months_since_activity: int) -> tuple[float, float]:
    """Return (decayed_zeq, decay_factor)."""
    raw = max(0.0, float(zeq))
    decayed = apply_decay(raw, int(months_since_activity))
    factor = round(decayed / raw, 4) if raw > 0 else 1.0
    return round(decayed, 4), factor
