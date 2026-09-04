"""Admin platform health — LinkedIn-style status for ZenK services."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.services.admin_platform_health import build_platform_health

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/platform-health",
    tags=["admin-platform-health"],
    dependencies=[Depends(require_admin_api_key)],
)


class HealthCheckOut(BaseModel):
    id: str
    label: str
    status: str
    detail: str
    latency_ms: Optional[int] = None
    checked_at: Optional[str] = None
    href: Optional[str] = None


class HealthGroupOut(BaseModel):
    id: str
    label: str
    checks: list[HealthCheckOut] = Field(default_factory=list)


class PlatformHealthOut(BaseModel):
    generated_at: Optional[str] = None
    overall: str
    summary: str
    checked_in_ms: int = 0
    groups: list[HealthGroupOut] = Field(default_factory=list)
    incidents: list[dict[str, Any]] = Field(default_factory=list)


@router.get("", response_model=PlatformHealthOut)
async def get_platform_health(db: AsyncSession = Depends(get_db)) -> PlatformHealthOut:
    data = await build_platform_health(db)
    return PlatformHealthOut(**data)
