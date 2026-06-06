"""Live impact charts for sponsor My Circle (ZQA snapshots + circle students)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import SponsorCircle
from app.models.school import SchoolStudent, SchoolZqaSnapshot


def _month_key(dt: datetime) -> tuple[int, int]:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt.year, dt.month)


def _month_label(year: int, month: int) -> str:
    return datetime(year, month, 1).strftime("%B")


async def build_impact_improvement(
    db: AsyncSession,
    circle_id: str,
) -> dict[str, Any]:
    circle_res = await db.execute(
        select(SponsorCircle.name).where(SponsorCircle.id == circle_id)
    )
    circle_name = circle_res.scalar_one_or_none() or "Your circle"

    student_res = await db.execute(
        select(SchoolStudent.id).where(SchoolStudent.circle_id == circle_id)
    )
    student_ids = [row[0] for row in student_res.all()]
    if not student_ids:
        return {
            "available": False,
            "message": (
                "Impact improvement appears after a school enrolls a student and "
                "submits at least one finalized ZQA report."
            ),
            "months": [],
            "summary": None,
            "circle_name": circle_name,
            "show_national_benchmark": False,
        }

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=95)

    snap_res = await db.execute(
        select(SchoolZqaSnapshot)
        .where(
            SchoolZqaSnapshot.student_id.in_(student_ids),
            SchoolZqaSnapshot.computed_at >= window_start.replace(tzinfo=None),
        )
        .order_by(SchoolZqaSnapshot.computed_at.asc())
    )
    circle_snaps = list(snap_res.scalars().all())

    if not circle_snaps:
        return {
            "available": False,
            "message": (
                "No ZQA history yet for your sponsored students. "
                "Finalize a quarterly report at the school to unlock this chart."
            ),
            "months": [],
            "summary": None,
            "circle_name": circle_name,
            "show_national_benchmark": False,
        }

    by_month: dict[tuple[int, int], list[float]] = defaultdict(list)
    for snap in circle_snaps:
        dt = snap.computed_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        pts = float(snap.zqa_baseline_delta or snap.zenq_contribution or 0)
        by_month[_month_key(dt)].append(pts)

    platform_res = await db.execute(
        select(SchoolZqaSnapshot)
        .where(SchoolZqaSnapshot.computed_at >= window_start.replace(tzinfo=None))
    )
    platform_by_month: dict[tuple[int, int], list[float]] = defaultdict(list)
    for snap in platform_res.scalars().all():
        dt = snap.computed_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        platform_by_month[_month_key(dt)].append(
            float(snap.zqa_baseline_delta or snap.zenq_contribution or 0)
        )

    month_keys = sorted(by_month.keys())[-3:]
    months_out = []
    for key in month_keys:
        us_vals = by_month[key]
        us_avg = int(round(sum(us_vals) / len(us_vals))) if us_vals else 0
        plat_vals = platform_by_month.get(key, [])
        top_avg: Optional[int] = None
        if len(plat_vals) >= 3:
            top_avg = int(round(max(plat_vals)))
        months_out.append(
            {
                "month": _month_label(key[0], key[1]),
                "us": us_avg,
                "top": top_avg,
            }
        )

    show_benchmark = any(m.get("top") is not None for m in months_out)
    summary = None
    if len(months_out) >= 2:
        first_us = months_out[0]["us"] or 0
        last_us = months_out[-1]["us"] or 0
        delta = last_us - first_us
        summary = (
            f"{circle_name} gained an average of {last_us} impact points in "
            f"{months_out[-1]['month']} "
            f"({delta:+d} vs {months_out[0]['month']}). "
            + (
                "National benchmark bars show the top circle that month."
                if show_benchmark
                else "National benchmarks appear when more circles publish ZQA data."
            )
        )
    elif len(months_out) == 1:
        summary = (
            f"{circle_name} recorded {months_out[0]['us']} impact points in "
            f"{months_out[0]['month']} from school ZQA reports."
        )

    return {
        "available": True,
        "message": None,
        "months": months_out,
        "summary": summary,
        "circle_name": circle_name,
        "show_national_benchmark": show_benchmark,
    }
