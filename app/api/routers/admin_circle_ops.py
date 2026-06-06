"""Admin circle management: registry, activity, and membership ops queue."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.microservices.sponsor_circle.schemas import CircleAdminRequestOut
from app.services.admin_circle_overview import (
    admin_circles_summary,
    get_admin_circle_detail,
    list_admin_circles,
)
from app.services.circle_membership_ops import (
    admin_review_request,
    list_pending_admin_queue,
    request_to_dict,
)

router = APIRouter(
    prefix="/admin/circle-ops",
    tags=["admin-circle-ops"],
    dependencies=[Depends(require_admin_api_key)],
)


class AdminCircleOpsDecision(BaseModel):
    decision: str = Field(..., description="approved or rejected")
    admin_comment: str = Field(..., min_length=5, max_length=2000)


class AdminCircleMemberRow(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    joined_at: Optional[str] = None
    hours_this_month: float = 0
    messages_count: int = 0
    orders_count: int = 0
    enrollment_reviews_count: int = 0
    participation_pct: int = 0
    pending_removal: bool = False


class AdminCircleListItem(BaseModel):
    id: str
    name: str
    status: str
    member_count: int
    member_limit: int
    created_at: Optional[str] = None
    leader_name: Optional[str] = None
    circle_hours_month: float = 0
    pending_ops_count: int = 0


class AdminCircleDetailOut(AdminCircleListItem):
    description: Optional[str] = None
    annual_budget: Optional[int] = None
    budget_spent: Optional[int] = None
    members: list[AdminCircleMemberRow] = Field(default_factory=list)


class AdminCirclesSummaryOut(BaseModel):
    total_circles: int
    total_members: int
    pending_ops_count: int
    total_hours_month: float


@router.get("/summary", response_model=AdminCirclesSummaryOut)
async def circle_ops_summary(db: AsyncSession = Depends(get_db)):
    return AdminCirclesSummaryOut(**await admin_circles_summary(db))


@router.get("/circles", response_model=list[AdminCircleListItem])
async def list_all_circles(db: AsyncSession = Depends(get_db)):
    return [AdminCircleListItem(**row) for row in await list_admin_circles(db)]


@router.get("/circles/{circle_id}", response_model=AdminCircleDetailOut)
async def get_circle_detail(circle_id: str, db: AsyncSession = Depends(get_db)):
    row = await get_admin_circle_detail(db, circle_id)
    if not row:
        raise HTTPException(status_code=404, detail="Circle not found.")
    return AdminCircleDetailOut(**row)


@router.get("/pending", response_model=list[CircleAdminRequestOut])
async def list_pending_circle_ops(db: AsyncSession = Depends(get_db)):
    rows = await list_pending_admin_queue(db)
    return [CircleAdminRequestOut(**r) for r in rows]


@router.patch("/requests/{request_id}", response_model=CircleAdminRequestOut)
async def review_circle_ops_request(
    request_id: str,
    body: AdminCircleOpsDecision,
    db: AsyncSession = Depends(get_db),
):
    try:
        req = await admin_review_request(
            db,
            request_id=request_id,
            decision=body.decision,
            admin_comment=body.admin_comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    from app.chat.models import SponsorCircle
    from sqlalchemy import select

    name_res = await db.execute(
        select(SponsorCircle.name).where(SponsorCircle.id == req.circle_id)
    )
    circle_name = name_res.scalar_one_or_none()

    try:
        from app.services.kia_event_briefings import (
            emit_member_limit_approved,
            emit_member_removal_processed,
        )

        if body.decision == "approved":
            if req.request_type == "member_removal":
                await emit_member_removal_processed(db, req=req, circle_name=circle_name)
            else:
                await emit_member_limit_approved(db, req=req, circle_name=circle_name)
        from app.services.kia_event_briefings import emit_admin_circle_ops_reviewed

        await emit_admin_circle_ops_reviewed(
            db, req=req, circle_name=circle_name, decision=body.decision
        )
    except Exception:
        pass

    await db.commit()
    return CircleAdminRequestOut(**request_to_dict(req, circle_name=circle_name))
