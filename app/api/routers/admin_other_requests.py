"""Admin queue for non-membership circle requests (renames, etc.)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.microservices.sponsor_circle.schemas import CircleAdminRequestOut
from app.models.circle_ops import (
    REQUEST_TYPES_OTHER,
    STATUS_PENDING,
    CircleAdminRequest,
)
from app.services.circle_membership_ops import (
    admin_review_request,
    list_pending_other_requests_queue,
    request_to_dict,
)

router = APIRouter(
    prefix="/admin/other-requests",
    tags=["admin-other-requests"],
    dependencies=[Depends(require_admin_api_key)],
)


class AdminOtherRequestsDecision(BaseModel):
    decision: str = Field(..., description="approved or rejected")
    admin_comment: str = Field(..., min_length=5, max_length=2000)


class AdminOtherRequestsSummaryOut(BaseModel):
    pending_count: int


@router.get("/summary", response_model=AdminOtherRequestsSummaryOut)
async def other_requests_summary(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(func.count())
        .select_from(CircleAdminRequest)
        .where(
            CircleAdminRequest.status == STATUS_PENDING,
            CircleAdminRequest.request_type.in_(sorted(REQUEST_TYPES_OTHER)),
        )
    )
    return AdminOtherRequestsSummaryOut(pending_count=int(res.scalar_one() or 0))


@router.get("/pending", response_model=list[CircleAdminRequestOut])
async def list_pending_other_requests(db: AsyncSession = Depends(get_db)):
    rows = await list_pending_other_requests_queue(db)
    return [CircleAdminRequestOut(**r) for r in rows]


@router.patch("/requests/{request_id}", response_model=CircleAdminRequestOut)
async def review_other_request(
    request_id: str,
    body: AdminOtherRequestsDecision,
    db: AsyncSession = Depends(get_db),
):
    from app.chat.models import SponsorCircle

    existing = await db.execute(
        select(CircleAdminRequest).where(CircleAdminRequest.id == request_id)
    )
    pre = existing.scalar_one_or_none()
    if not pre:
        raise HTTPException(status_code=404, detail="Request not found.")
    if pre.request_type not in REQUEST_TYPES_OTHER:
        raise HTTPException(
            status_code=400,
            detail="This request is handled under Admin → Circle ops.",
        )

    try:
        req = await admin_review_request(
            db,
            request_id=request_id,
            decision=body.decision,
            admin_comment=body.admin_comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    name_res = await db.execute(
        select(SponsorCircle.name).where(SponsorCircle.id == req.circle_id)
    )
    circle_name = name_res.scalar_one_or_none()

    try:
        from app.services.kia_event_briefings import emit_admin_circle_ops_reviewed

        await emit_admin_circle_ops_reviewed(
            db, req=req, circle_name=circle_name, decision=body.decision
        )
    except Exception:
        pass

    await db.commit()
    return CircleAdminRequestOut(**request_to_dict(req, circle_name=circle_name))
