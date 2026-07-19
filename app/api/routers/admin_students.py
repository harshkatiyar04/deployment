"""Admin student progress — list + detail (admin session / API key)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.services.admin_student_progress import (
    get_admin_student_progress,
    list_admin_students,
)

router = APIRouter(
    prefix="/admin/students",
    tags=["admin-students"],
    dependencies=[Depends(require_admin_api_key)],
)


@router.get("")
async def admin_list_students(
    q: Optional[str] = Query(None, max_length=200),
    circle_id: Optional[str] = Query(None),
    kyc_status: Optional[str] = Query(None),
    roster: str = Query("all", pattern="^(all|yes|no)$"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await list_admin_students(
        db,
        q=q,
        circle_id=circle_id,
        kyc_status=kyc_status,
        roster=roster,
    )


@router.get("/{signup_id}")
async def admin_student_progress(
    signup_id: str,
    quarter: Optional[str] = Query(None, max_length=8),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await get_admin_student_progress(db, signup_id, quarter=quarter)
    if not data:
        raise HTTPException(status_code=404, detail="Student not found")
    return data
