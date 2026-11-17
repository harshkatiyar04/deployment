"""Ingest holistic school ZQA into zenq_v2_assessments (MEAN_FIRST_TWO source)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.zenq_v2.zqa_map import holistic_to_assessment_row

logger = logging.getLogger(__name__)


def _as_uuid(value: Optional[str]) -> Optional[UUID]:
    if value is None or value == "":
        return None
    return UUID(str(value))


async def ensure_circle_profile(db: AsyncSession, circle_id: str) -> dict[str, Any]:
    row = (
        await db.execute(
            text(
                """
                SELECT need_band, k, bracket, activated_on
                FROM "ZENK"."zenq_v2_circle_profile"
                WHERE circle_id = CAST(:c AS uuid)
                """
            ),
            {"c": circle_id},
        )
    ).mappings().first()
    if row:
        return dict(row)

    await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_circle_profile"(
                circle_id, need_band, k, activated_on, bracket, updated_at
            ) VALUES (
                :c, 'Developing', 1.0, CURRENT_DATE, 'B', NOW()
            )
            ON CONFLICT (circle_id) DO NOTHING
            """
        ),
        {"c": _as_uuid(circle_id)},
    )
    return {
        "need_band": "Developing",
        "k": 1.0,
        "bracket": "B",
        "activated_on": None,
    }


async def ingest_circle_assessments(db: AsyncSession, circle_id: str) -> int:
    """Pull ZenqStudentContext into zenq_v2_assessments. Idempotent. Returns inserts."""
    inserted = 0
    try:
        ctx = (
            await db.execute(
                text(
                    """
                    SELECT student_id::text AS student_id,
                           zqa_composite,
                           baseline_zqa,
                           updated_at
                    FROM "ZENK"."zenq_student_context"
                    WHERE circle_id = :c
                      AND zqa_composite IS NOT NULL
                    """
                ),
                {"c": _as_uuid(circle_id)},
            )
        ).mappings().all()
    except Exception:
        logger.debug("[zenq_v2] zenq_student_context unavailable for %s", circle_id, exc_info=True)
        ctx = []

    for row in ctx:
        student_id = row["student_id"]
        composite = float(row["zqa_composite"] or 0)
        baseline = row.get("baseline_zqa")
        assessed_on = row.get("updated_at")
        if assessed_on is None:
            continue
        day = assessed_on.date() if hasattr(assessed_on, "date") else assessed_on

        if baseline is not None:
            mapped_b = holistic_to_assessment_row(float(baseline), is_baseline=True)
            inserted += await _upsert_assessment(
                db,
                circle_id=circle_id,
                student_id=student_id,
                assessed_on=day,
                mapped=mapped_b,
                force_day_offset_days=-1,
            )

        mapped = holistic_to_assessment_row(composite, is_baseline=False)
        inserted += await _upsert_assessment(
            db,
            circle_id=circle_id,
            student_id=student_id,
            assessed_on=day,
            mapped=mapped,
            force_day_offset_days=0,
        )

    return inserted


async def _upsert_assessment(
    db: AsyncSession,
    *,
    circle_id: str,
    student_id: Optional[str],
    assessed_on,
    mapped: dict[str, Any],
    force_day_offset_days: int = 0,
) -> int:
    day = assessed_on
    if force_day_offset_days:
        try:
            day = day + timedelta(days=force_day_offset_days)
        except Exception:
            pass

    sid = _as_uuid(student_id)
    cid = _as_uuid(circle_id)
    ib = bool(mapped.get("is_baseline"))
    if sid is None:
        existing = (
            await db.execute(
                text(
                    """
                    SELECT id FROM "ZENK"."zenq_v2_assessments"
                    WHERE circle_id = :c AND assessed_on = :d
                      AND student_id IS NULL
                      AND COALESCE(is_baseline, false) = :ib
                    LIMIT 1
                    """
                ),
                {"c": cid, "d": day, "ib": ib},
            )
        ).scalar()
    else:
        existing = (
            await db.execute(
                text(
                    """
                    SELECT id FROM "ZENK"."zenq_v2_assessments"
                    WHERE circle_id = :c AND assessed_on = :d
                      AND student_id = :s
                      AND COALESCE(is_baseline, false) = :ib
                    LIMIT 1
                    """
                ),
                {"c": cid, "d": day, "s": sid, "ib": ib},
            )
        ).scalar()
    if existing is not None:
        return 0

    await db.execute(
        text(
            """
            INSERT INTO "ZENK"."zenq_v2_assessments"(
                circle_id, student_id, assessed_on, language, maths, history,
                composite, is_baseline, source
            ) VALUES (
                :c, :s, :d, :lang, :maths, :hist, :comp, :ib, :src
            )
            """
        ),
        {
            "c": cid,
            "s": sid,
            "d": day,
            "lang": mapped.get("language"),
            "maths": mapped.get("maths"),
            "hist": mapped.get("history"),
            "comp": mapped["composite"],
            "ib": ib,
            "src": mapped.get("source") or "holistic_v2_equal_split",
        },
    )
    return 1
