"""ZenQ v2 dual-run APIs (member wall, dashboard, admin close/agent)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.core.settings import settings
from app.db.session import get_db
from app.services.zenq_v2.agent import list_agent_runs, review_agent_run, run_agent_for_month
from app.services.zenq_v2.close import close_month
from app.services.zenq_v2.dashboard import get_circle_dashboard, get_circle_statement
from app.services.zenq_v2.ledger import get_member_me, rebuild_pcs
from app.services.zenq_v2.epr import list_partners
from app.services.zenq_v2.market import season_ladder, season_reset_preview
from app.services.zenq_v2.recalibration import (
    get_latest_recalibration,
    list_recalibration_runs,
    list_sealed_predictions,
    log_recalibration,
    recalibration_status,
    review_recalibration,
    seal_prediction,
)
from app.services.zenq_v2.referrals import (
    activate_referral,
    grant_spark,
    member_spark_referral_summary,
    referral_ready,
)
from app.services.zenq_v2.sponsor_csr import (
    csr_allocation_run,
    csr_status,
    list_csr_runs,
    list_sponsor_circles,
    list_sponsors_for_admin,
)
from app.services.zenq_v2.status import zenq_v2_pipeline_status
from app.services.zenq_v2.weights import get_latest_factor_weights, list_factor_weights

router = APIRouter(prefix="/zenq/v2", tags=["zenq-v2"])
admin_router = APIRouter(
    prefix="/admin/zenq/v2",
    tags=["admin-zenq-v2"],
    dependencies=[Depends(require_admin_api_key)],
)


class CloseRequest(BaseModel):
    month: date
    circle_ids: Optional[list[str]] = None
    admin_trigger: bool = True


class AgentRunRequest(BaseModel):
    month: date
    signals: Optional[dict[str, Any]] = None


class AgentReviewRequest(BaseModel):
    reviewed_by: str = Field(min_length=1, max_length=128)
    approve: bool = True


class RecalibrationRequest(BaseModel):
    pairs: Optional[int] = Field(None, ge=0)
    proposed_shift: dict[str, float] = Field(default_factory=dict)
    notes: Optional[str] = None


class RecalibrationReviewRequest(BaseModel):
    reviewed_by: str = Field(min_length=1, max_length=128)
    approve: bool = True


class SealPredictionRequest(BaseModel):
    label: str
    value: Any
    open_at_month_6: bool = True


class CsrAllocateRequest(BaseModel):
    budget_inr: float = Field(gt=0)
    notes: Optional[str] = None
    sponsor_id: Optional[str] = None
    weights: Optional[list[float]] = None
    as_of_month: Optional[date] = None
    force: bool = False


class SparkGrantRequest(BaseModel):
    actor_id: str
    circle_id: str
    spark_id: Optional[str] = None
    reason: Optional[str] = None


class ReferralActivateRequest(BaseModel):
    actor_id: str
    circle_id: str
    sessions_completed: int = Field(ge=0)
    first_pledge_paid: bool = False
    referred_circle_id: Optional[str] = None


class KiaEmitRequest(BaseModel):
    actor_id: Optional[str] = None
    circle_id: str
    kia_kind: str = Field(description="PRACTICE | PREP | EFFECTIVE")
    idempotency_key: Optional[str] = None


@router.get("/status")
async def v2_status() -> dict:
    return zenq_v2_pipeline_status()


@router.get("/members/{member_id}/me")
async def member_me(
    member_id: str,
    circle_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not (settings.zenq_v2_ledger or settings.zenq_v2_product):
        return {
            "scored": False,
            "message": "not yet scored",
            "pipeline": "off",
            **zenq_v2_pipeline_status(),
        }
    return await get_member_me(db, member_id, circle_id)


@router.get("/circles/{circle_id}/dashboard")
async def circle_dashboard(circle_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    if not (settings.zenq_v2_close or settings.zenq_v2_product):
        return {"scored": False, "message": "not yet scored", "circle_id": circle_id}
    return await get_circle_dashboard(db, circle_id)


@router.get("/circles/{circle_id}/statement")
async def circle_statement(
    circle_id: str,
    month: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not (settings.zenq_v2_close or settings.zenq_v2_product):
        return {"scored": False, "message": "not yet scored", "circle_id": circle_id}
    return await get_circle_statement(db, circle_id, month)


@router.get("/market/ladder")
async def market_ladder(
    bracket: str = Query("B", pattern="^[ABC]$"),
    season_key: str = Query("current"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await season_ladder(db, bracket=bracket, season_key=season_key)


@admin_router.get("/market/ladder")
async def admin_market_ladder(
    bracket: str = Query("B", pattern="^[ABC]$"),
    season_key: str = Query("current"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await season_ladder(db, bracket=bracket, season_key=season_key)


@admin_router.get("/market/season-reset-preview")
async def admin_season_reset_preview(db: AsyncSession = Depends(get_db)) -> dict:
    return await season_reset_preview(db)


@router.get("/partners")
async def partners_marketplace(
    track: Optional[str] = Query(None, pattern="^(TUTOR|MENTOR)$"),
    sort: str = Query("epr", pattern="^(epr|confidence)$"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Education partner marketplace — EPR + confidence; no child ids."""
    if not (
        settings.zenq_v2_product
        or settings.zenq_v2_close
        or settings.zenq_v2_ledger
    ):
        return {"items": [], "sort": sort, "track": track, "pipeline": "off"}
    return await list_partners(db, track=track, sort=sort, limit=limit)


@admin_router.get("/partners")
async def admin_partners_marketplace(
    track: Optional[str] = Query(None, pattern="^(TUTOR|MENTOR)$"),
    sort: str = Query("epr", pattern="^(epr|confidence)$"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await list_partners(db, track=track, sort=sort, limit=limit)


@admin_router.get("/spark-referral/status")
async def admin_spark_referral_status(
    actor_id: str = Query(...),
    circle_id: str = Query(...),
    sessions_completed: int = Query(0, ge=0),
    first_pledge_paid: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import select

    from app.chat.models import SponsorCircle
    from app.models.signup import SignupRequest
    from app.services.admin_zenq_observatory import circle_member_roster

    summary = await member_spark_referral_summary(
        db, member_id=actor_id, circle_id=circle_id
    )
    summary["referral_ready"] = referral_ready(
        sessions_completed=sessions_completed, first_pledge_paid=first_pledge_paid
    )
    summary["sessions_completed"] = sessions_completed
    summary["first_pledge_paid"] = first_pledge_paid

    circle = (
        await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
    ).scalar_one_or_none()
    summary["circle_name"] = getattr(circle, "name", None) if circle else None
    actor = (
        await db.execute(select(SignupRequest).where(SignupRequest.id == actor_id))
    ).scalar_one_or_none()
    summary["actor_name"] = (actor.full_name or actor.email) if actor else None
    summary["roster"] = await circle_member_roster(db, circle_id)
    return summary


@admin_router.post("/spark/grant")
async def admin_grant_spark(body: SparkGrantRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Admin verify — Grant Spark (LOGGED to ledger). Irreversible; ≤2/year."""
    return await grant_spark(
        db,
        actor_id=body.actor_id,
        circle_id=body.circle_id,
        spark_id=body.spark_id,
        reason=body.reason or "admin_lab",
    )


@admin_router.post("/referral/activate")
async def admin_activate_referral(
    body: ReferralActivateRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    return await activate_referral(
        db,
        actor_id=body.actor_id,
        circle_id=body.circle_id,
        sessions_completed=body.sessions_completed,
        first_pledge_paid=body.first_pledge_paid,
        referred_circle_id=body.referred_circle_id,
    )


@admin_router.post("/kia/emit")
async def admin_emit_kia(body: KiaEmitRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Admin verify — emit KIA_PRACTICE / PREP / EFFECTIVE into the v2 ledger."""
    from app.services.zenq_v2.bridge import bridge_kia

    return await bridge_kia(
        db,
        circle_id=body.circle_id,
        actor_user_id=body.actor_id,
        kia_kind=body.kia_kind,
        idempotency_key=body.idempotency_key,
    )


@router.get("/sponsor/{sponsor_id}/circles")
async def sponsor_circles(sponsor_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    return await list_sponsor_circles(db, sponsor_id)


@admin_router.get("/status")
async def admin_v2_status() -> dict:
    return zenq_v2_pipeline_status()


@admin_router.post("/close")
async def admin_close(body: CloseRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return await close_month(
        db, body.month, circle_ids=body.circle_ids, admin_trigger=body.admin_trigger
    )


@admin_router.post("/members/{member_id}/rebuild-pcs")
async def admin_rebuild_pcs(
    member_id: str,
    circle_id: str = Query(...),
    months_silent: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    pcs = await rebuild_pcs(db, member_id, circle_id, months_silent=months_silent)
    return {"ok": True, "pcs": pcs}


@admin_router.get("/weights")
async def admin_v2_factor_weights(
    limit: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Phase 2b: factor_weights_month history + ν (audit)."""
    latest = await get_latest_factor_weights(db)
    items = await list_factor_weights(db, limit=limit)
    st = zenq_v2_pipeline_status()
    return {
        "latest": latest,
        "items": items,
        "agent_apply": st["launch_dials"]["agent_apply"],
        "note": "ν = 1.0 while weights unchanged; agent.apply false → LOGGED proposals never mutate live weights",
    }


@admin_router.post("/agent/run")
async def admin_agent_run(body: AgentRunRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return await run_agent_for_month(db, body.month, body.signals)


@admin_router.get("/agent/runs")
async def admin_agent_runs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return {"items": await list_agent_runs(db, limit=limit)}


@admin_router.post("/agent/runs/{run_id}/review")
async def admin_agent_review(
    run_id: str, body: AgentReviewRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    return await review_agent_run(
        db, run_id, reviewed_by=body.reviewed_by, approve_note=body.approve
    )


@admin_router.post("/recalibration")
async def admin_recalibration(
    body: RecalibrationRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    return await log_recalibration(
        db, pairs=body.pairs, proposed_shift=body.proposed_shift, notes=body.notes
    )


@admin_router.get("/recalibration/status")
async def admin_recalibration_status(db: AsyncSession = Depends(get_db)) -> dict:
    return await recalibration_status(db)


@admin_router.get("/recalibration/latest")
async def admin_recalibration_latest(db: AsyncSession = Depends(get_db)) -> dict:
    return await get_latest_recalibration(db)


@admin_router.get("/recalibration/runs")
async def admin_recalibration_runs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await list_recalibration_runs(db, limit=limit)


@admin_router.post("/recalibration/runs/{run_id}/review")
async def admin_recalibration_review(
    run_id: str,
    body: RecalibrationReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await review_recalibration(
        db, run_id, reviewed_by=body.reviewed_by, approve=body.approve
    )


@admin_router.post("/predictions/seal")
async def admin_seal_prediction(
    body: SealPredictionRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    return await seal_prediction(
        db, body.label, body.value, month_6=body.open_at_month_6
    )


@admin_router.get("/predictions/sealed")
async def admin_list_sealed(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return {"items": await list_sealed_predictions(db, limit=limit)}


@admin_router.get("/csr/status")
async def admin_csr_status(db: AsyncSession = Depends(get_db)) -> dict:
    return await csr_status(db)


@admin_router.get("/csr/sponsors")
async def admin_csr_sponsors(
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await list_sponsors_for_admin(db, limit=limit)


@admin_router.get("/csr/runs")
async def admin_csr_runs(
    limit: int = Query(20, ge=1, le=100),
    sponsor_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await list_csr_runs(db, limit=limit, sponsor_id=sponsor_id)


@admin_router.post("/csr/allocate")
async def admin_csr_allocate(
    body: CsrAllocateRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    return await csr_allocation_run(
        db,
        budget_inr=body.budget_inr,
        notes=body.notes,
        sponsor_id=body.sponsor_id,
        weights=body.weights,
        as_of_month=body.as_of_month,
        force=body.force,
    )
