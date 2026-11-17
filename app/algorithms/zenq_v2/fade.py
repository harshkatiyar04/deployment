"""Member inactivity fade — never applied to circle stock."""

from __future__ import annotations

from typing import Any, Optional

from app.algorithms.zenq_v2.params import LAUNCH_PARAMS


def fade_factor(months_silent: int, params: Optional[dict[str, Any]] = None) -> float:
    p = params or LAUNCH_PARAMS
    after = int(p["fade_after"])
    rate = float(p["fade_rate"])
    return (1.0 - rate) ** max(0, int(months_silent) - after)
