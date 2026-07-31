"""
Leader/member eCollection dashboard routes — JWT protected.

Does NOT modify disbursement, chat, or budget set endpoints.
UAT simulate is env-gated. Leaders may pick remitter (default KYC);
members may simulate only as themselves (remitter forced to KYC).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import get_current_user
from app.db.session import get_db
from app.models.signup import SignupRequest
from app.services.circle_budget import _can_set_budget, resolve_user_circle
from app.banking.services.circle_ecollection_dashboard import (
    build_collections_dashboard,
    build_member_contribute,
    simulate_bank_credit,
    simulate_enabled,
)

router = APIRouter(prefix="/sponsor-circle", tags=["Sponsor Circle eCollection"])


class SimulateCreditRequest(BaseModel):
    circle_id: Optional[str] = None
    amount_inr: str = Field(default="100.00", max_length=20)
    remitter_name: str = Field(default="", max_length=30)
    payment_mode: str = Field(default="UPI", max_length=16)


def _kyc_remitter(user: SignupRequest) -> str:
    return (getattr(user, "full_name", None) or "").strip()[:30]


@router.get("/ecollection")
async def get_ecollection_dashboard(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    circle, role = await resolve_user_circle(db, user.id, circle_id)
    data = await build_collections_dashboard(db, circle=circle)
    is_leader = bool(_can_set_budget(role))
    data["can_simulate"] = bool(simulate_enabled() and is_leader)
    data["is_leader"] = is_leader
    data["kyc_full_name"] = _kyc_remitter(user) or None
    data["default_remitter_name"] = data["kyc_full_name"]
    # Members must not scrape peer remitter names from Collect history
    if not is_leader:
        data["recent_credits"] = []
        data["credit_count"] = 0
        data["total_credited_inr"] = 0
    await db.commit()  # persist auto-created VAN
    return data


@router.get("/contribute")
async def get_member_contribute(
    circle_id: Optional[str] = None,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Member pay-in: VAN details + credits attributed to this user only."""
    circle, _role = await resolve_user_circle(db, user.id, circle_id)
    data = await build_member_contribute(db, circle=circle, user=user)
    data["can_simulate"] = bool(simulate_enabled())
    data["gateway_ready"] = False
    data["default_remitter_name"] = data.get("kyc_full_name")
    await db.commit()
    return data


@router.post("/ecollection/simulate-credit")
async def post_simulate_credit(
    body: SimulateCreditRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not simulate_enabled():
        raise HTTPException(
            status_code=403,
            detail="Credit simulation is disabled on this environment.",
        )
    circle, _role = await resolve_user_circle(db, user.id, body.circle_id)
    kyc = _kyc_remitter(user)
    if not kyc:
        raise HTTPException(
            status_code=400,
            detail="Complete your KYC full name before simulating a credit. Remitter is locked to your profile name.",
        )
    # Always use the signed-in user's KYC — never allow forged remitter names.
    remitter = kyc
    try:
        result = await simulate_bank_credit(
            db,
            circle=circle,
            user_id=user.id,
            amount_inr=body.amount_inr,
            remitter_name=remitter,
            payment_mode=body.payment_mode,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return result
