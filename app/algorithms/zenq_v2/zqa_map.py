"""Map live holistic school ZQA composite into v2 assessment composite.

Board text still cites Language 40 / Maths 35 / History 25. Live school ZQA is
holistic (academic + Bloom + SEL). Until a board workshop locks the split, we
store the holistic composite in all three subject slots equally so GrowthRatio
and SGI can run on one number.
"""

from __future__ import annotations

from typing import Any


def holistic_to_assessment_row(composite: float, *, is_baseline: bool = False) -> dict[str, Any]:
    c = float(composite)
    return {
        "language": c,
        "maths": c,
        "history": c,
        "composite": c,
        "is_baseline": is_baseline,
        "source": "holistic_v2_equal_split",
    }
