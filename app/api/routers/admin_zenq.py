"""Admin ZenQ algorithm observatory (Phase 0 — read-only scrutiny + backfill)."""

import json
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.core.rate_limit import limiter
from app.db.session import SessionLocal, get_db
from app.services.admin_zenq_observatory import (
    get_zenq_circle_detail,
    list_zenq_circles,
    list_zenq_snapshots,
    run_zenq_backfill,
    run_zenq_recompute_circle,
    zenq_engine_status,
)
from app.services.zenq_backfill import backfill_all_circles_progress
from app.services.zenq_welfare_scan import (
    list_open_welfare_cases,
    resolve_welfare_case,
    run_welfare_scan_all_circles,
)
from app.algorithms.zenq.score_scales import algorithm_reference
from app.services.zenq_weight_recalibration import (
    approve_weight_proposal,
    list_weight_configs,
    propose_weight_recalibration,
    reject_weight_proposal,
)

router = APIRouter(
    prefix="/admin/zenq",
    tags=["admin-zenq"],
    dependencies=[Depends(require_admin_api_key)],
)


class ZenqBackfillResult(BaseModel):
    total_circles: int
    processed: int
    failed: int
    errors: list[dict[str, str]] = Field(default_factory=list)


class ZenqRecomputeResult(BaseModel):
    ok: bool
    ziq: Optional[float] = None
    zeq_avg: Optional[float] = None
    zcq: Optional[float] = None
    error: Optional[str] = None


class ZenqWelfareResolveRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=2000)


class ZenqWeightProposalRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=2000)
    force: bool = False


class ZenqWeightDecisionRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=2000)


@router.get("/status")
async def zenq_status(db: AsyncSession = Depends(get_db)) -> dict:
    return await zenq_engine_status(db)


@router.get("/algorithm-reference")
async def zenq_algorithm_reference() -> dict:
    return algorithm_reference()


@router.get("/circles")
async def zenq_circles(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    return await list_zenq_circles(db, limit=limit, offset=offset)


@router.get("/circles/{circle_id}")
async def zenq_circle_detail(
    circle_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    detail = await get_zenq_circle_detail(db, circle_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Circle not found")
    return detail


@router.get("/snapshots")
async def zenq_snapshots(
    db: AsyncSession = Depends(get_db),
    circle_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    return await list_zenq_snapshots(db, circle_id=circle_id, limit=limit, offset=offset)


@router.post("/backfill", response_model=ZenqBackfillResult)
@limiter.limit("6/hour")
async def zenq_backfill(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await run_zenq_backfill(db)


@router.post("/backfill/stream")
@limiter.limit("6/hour")
async def zenq_backfill_stream(request: Request):
    """NDJSON progress stream: start → progress (percent) → done.

    Owns its own DB session for the full stream lifetime (Depends(get_db)
    would close before the client finishes reading).
    """

    async def event_stream():
        async with SessionLocal() as db:
            async for event in backfill_all_circles_progress(db):
                yield json.dumps(event, default=str) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/circles/{circle_id}/recompute", response_model=ZenqRecomputeResult)
@limiter.limit("30/hour")
async def zenq_recompute_circle(
    request: Request,
    circle_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await run_zenq_recompute_circle(db, circle_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.get("/welfare")
async def zenq_welfare_cases(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=300),
) -> dict:
    items = await list_open_welfare_cases(db, limit=limit)
    return {"total": len(items), "items": items}


@router.post("/welfare/scan")
@limiter.limit("12/hour")
async def zenq_welfare_scan(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await run_welfare_scan_all_circles(db)


@router.post("/welfare/{case_id}/resolve")
@limiter.limit("60/hour")
async def zenq_welfare_resolve(
    request: Request,
    case_id: str,
    body: Annotated[ZenqWelfareResolveRequest, Body()],
    db: AsyncSession = Depends(get_db),
) -> dict:
    admin_email = getattr(request.state, "admin_email", None) or "admin"
    ok = await resolve_welfare_case(
        db,
        case_id,
        resolved_by=admin_email,
        notes=body.notes,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Welfare case not found or already resolved")
    return {"ok": True, "case_id": case_id}


@router.get("/weights")
async def zenq_weight_configs(db: AsyncSession = Depends(get_db)) -> dict:
    return await list_weight_configs(db)


@router.post("/weights/propose")
@limiter.limit("12/hour")
async def zenq_propose_weights(
    request: Request,
    body: Annotated[ZenqWeightProposalRequest, Body()],
    db: AsyncSession = Depends(get_db),
) -> dict:
    admin_email = getattr(request.state, "admin_email", None) or "admin"
    result = await propose_weight_recalibration(
        db,
        proposed_by=admin_email,
        notes=body.notes,
        force=body.force,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/weights/{proposal_id}/approve")
@limiter.limit("30/hour")
async def zenq_approve_weights(
    request: Request,
    proposal_id: str,
    body: Annotated[ZenqWeightDecisionRequest, Body()],
    db: AsyncSession = Depends(get_db),
) -> dict:
    admin_email = getattr(request.state, "admin_email", None) or "admin"
    result = await approve_weight_proposal(
        db,
        proposal_id,
        approved_by=admin_email,
        notes=body.notes,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.post("/weights/{proposal_id}/reject")
@limiter.limit("30/hour")
async def zenq_reject_weights(
    request: Request,
    proposal_id: str,
    body: Annotated[ZenqWeightDecisionRequest, Body()],
    db: AsyncSession = Depends(get_db),
) -> dict:
    admin_email = getattr(request.state, "admin_email", None) or "admin"
    result = await reject_weight_proposal(
        db,
        proposal_id,
        rejected_by=admin_email,
        notes=body.notes,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result
