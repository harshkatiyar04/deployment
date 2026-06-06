"""Normalize and format class rank fields (rank position vs class size)."""
from __future__ import annotations

import re
from typing import Optional, Tuple

_RANK_SLASH_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")


def normalize_class_rank_fields(
    rank_in_class: Optional[str],
    class_size: Optional[int],
) -> Tuple[Optional[str], Optional[int]]:
    """
    Store rank as position only (e.g. '3') and class_size as integer (e.g. 42).
    If user enters '3/42' in rank_in_class, split into both fields.
    """
    if rank_in_class is None and class_size is None:
        return None, class_size

    raw = str(rank_in_class).strip() if rank_in_class is not None else ""
    if not raw:
        return None, class_size

    m = _RANK_SLASH_RE.match(raw)
    if m:
        pos, total = int(m.group(1)), int(m.group(2))
        return str(pos), total

    if raw.isdigit() and class_size is not None:
        return raw, int(class_size)

    return raw, class_size


def format_class_rank_display(
    rank_in_class: Optional[str],
    class_size: Optional[int],
) -> Tuple[str, str]:
    """Return (primary_line, subtitle) for UI."""
    rank, size = normalize_class_rank_fields(rank_in_class, class_size)

    if not rank and size is None:
        return "N/A", "Rank not reported"

    if rank and size is not None:
        try:
            pos = int(rank)
            return f"{pos} / {size}", f"Rank {pos} of {size} in class"
        except ValueError:
            pass

    if rank and _RANK_SLASH_RE.match(str(rank)):
        m = _RANK_SLASH_RE.match(str(rank))
        pos, total = m.group(1), m.group(2)
        return f"{pos} / {total}", f"Rank {pos} of {total} in class"

    if rank:
        if size is not None:
            return str(rank), f"Position reported (class size {size})"
        return str(rank), "Class position"

    if size is not None:
        return f"— / {size}", f"Class size {size} (rank not set)"

    return "N/A", "Rank not reported"
