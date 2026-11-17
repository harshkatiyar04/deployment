"""Admin ZenQ observatory — v2 pipeline status + circle roster (no 1.5.1 materializer)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.core.settings import settings
from app.models.signup import SignupRequest
from app.services.zenq_v2.status import zenq_v2_pipeline_status


async def circle_member_roster(db: AsyncSession, circle_id: str) -> list[dict[str, Any]]:
    """Members with display names for Admin UX (no UUID hunting)."""
    rows = (
        await db.execute(
            select(
                CircleMember.user_id,
                CircleMember.role,
                SignupRequest.full_name,
                SignupRequest.email,
            )
            .join(SignupRequest, SignupRequest.id == CircleMember.user_id)
            .where(CircleMember.circle_id == circle_id)
            .order_by(SignupRequest.full_name.asc())
        )
    ).all()
    out: list[dict[str, Any]] = []
    for user_id, role, full_name, email in rows:
        out.append(
            {
                "user_id": user_id,
                "name": full_name or (email or user_id[:8]),
                "role": role,
                "email": email,
            }
        )
    return out


async def get_zenq_circle_detail(db: AsyncSession, circle_id: str) -> Optional[dict[str, Any]]:
    sc = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
    circle = sc.scalar_one_or_none()
    if not circle:
        return None
    roster = await circle_member_roster(db, circle_id)
    return {
        "circle_id": circle_id,
        "circle_name": getattr(circle, "name", None),
        "scored": False,
        "message": "Legacy 1.5.1 materializer archived — use ZenQ v2 close / dashboard.",
        "roster": roster,
        "sponsors": [
            {
                "user_id": m["user_id"],
                "name": m["name"],
                "role": m["role"],
            }
            for m in roster
            if str(m.get("role") or "").lower() in ("sponsor", "sponsor_leader", "lead")
        ],
        "legacy_materializer": False,
    }


async def zenq_engine_status(db: AsyncSession) -> dict[str, Any]:
    """Product status: v2-only. Legacy engine flags reported as unsupported."""
    v2 = zenq_v2_pipeline_status()
    if settings.zenq_engine_enabled:
        # Soft-block: do not re-arm materializer even if env is wrong.
        import logging

        logging.getLogger(__name__).warning(
            "ZENQ_ENGINE_ENABLED=true ignored — 1.5.1 board archived; product is ZenQ v2"
        )
    return {
        "algorithm_version": v2.get("v2_algorithm_version"),
        "product": "zenq_v2",
        "legacy_1_5_1_archived": True,
        "zenq_engine_enabled": False,
        "zenq_live_events": bool(settings.zenq_live_events),
        "zenq_recalibration_enabled": False,
        "circles_scored": None,
        "note": "1.5.1 board engine archived under archive/legacy/zenq-1.5.1-ras-ai/",
        "zenq_v2": {
            **v2,
            "flags": {
                **(v2.get("flags") or {}),
                "ZENQ_V2_LEDGER": bool(settings.zenq_v2_ledger),
                "ZENQ_V2_CLOSE": bool(settings.zenq_v2_close),
                "ZENQ_V2_PRODUCT": bool(settings.zenq_v2_product),
            },
        },
    }
