"""Admin ZenQ observatory — v2-only (legacy 1.5.1 materializer archived)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.services.admin_zenq_observatory import get_zenq_circle_detail, zenq_engine_status

router = APIRouter(
    prefix="/admin/zenq",
    tags=["admin-zenq"],
    dependencies=[Depends(require_admin_api_key)],
)


@router.get("/status")
async def zenq_status(db: AsyncSession = Depends(get_db)) -> dict:
    return await zenq_engine_status(db)


@router.get("/circles/{circle_id}")
async def zenq_circle_detail(
    circle_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Roster + names for Admin Lab (Spark/CSR); no 1.5.1 score materialization."""
    detail = await get_zenq_circle_detail(db, circle_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Circle not found")
    return detail


@router.get("/circles")
async def zenq_circles(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """Active sponsor circles by name (not legacy zenq_circle_scores)."""
    from sqlalchemy import select

    from app.chat.models import SponsorCircle

    total_q = await db.execute(select(SponsorCircle.id))
    total = len(total_q.all())
    rows = (
        await db.execute(
            select(SponsorCircle)
            .order_by(SponsorCircle.name.asc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    return {
        "total": total,
        "items": [
            {
                "circle_id": c.id,
                "circle_name": c.name,
                "status": c.status,
            }
            for c in rows
        ],
        "source": "sponsor_circles",
        "legacy_materializer": False,
    }
