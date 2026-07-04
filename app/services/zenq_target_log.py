"""Leader-logged target achievement for ZenQ (Phase 2)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zenq import ZenqTargetLog
from app.services.zenq_sponsor_enrichment import VALID_TARGET_STATUSES, current_fy_quarter
from app.services.zenq_event_processor import process_target_log_event


async def create_target_log(
    db: AsyncSession,
    *,
    circle_id: str,
    sponsor_user_id: str,
    target_status: str,
    logged_by_user_id: str,
    notes: Optional[str] = None,
    quarter: Optional[str] = None,
    fy: Optional[str] = None,
) -> dict[str, Any]:
    status = (target_status or "").lower().strip()
    if status not in VALID_TARGET_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"target_status must be one of: {', '.join(sorted(VALID_TARGET_STATUSES))}",
        )

    q_key, fy_key = current_fy_quarter()
    quarter = (quarter or q_key).upper()
    fy = fy or fy_key

    row = ZenqTargetLog(
        circle_id=circle_id,
        sponsor_user_id=sponsor_user_id,
        quarter=quarter,
        fy=fy,
        target_status=status,
        notes=(notes or "").strip() or None,
        logged_by_user_id=logged_by_user_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    await process_target_log_event(
        circle_id=circle_id,
        sponsor_user_id=sponsor_user_id,
        target_status=status,
        log_id=row.id,
    )

    return {
        "id": row.id,
        "circle_id": circle_id,
        "sponsor_user_id": sponsor_user_id,
        "quarter": quarter,
        "fy": fy,
        "target_status": status,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
