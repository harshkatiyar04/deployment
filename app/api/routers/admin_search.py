"""Admin global search — unified record lookup across ops modules."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.services.admin_global_search import run_admin_global_search

router = APIRouter(
    prefix="/admin/search",
    tags=["admin-search"],
    dependencies=[Depends(require_admin_api_key)],
)


class AdminSearchRecordOut(BaseModel):
    id: str
    title: str
    subtitle: str
    href: str
    group: str
    group_label: str


class AdminSearchGroupOut(BaseModel):
    type: str
    label: str
    items: list[AdminSearchRecordOut]


class AdminSearchOut(BaseModel):
    query: str
    groups: list[AdminSearchGroupOut]


@router.get("", response_model=AdminSearchOut)
async def admin_global_search(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
) -> AdminSearchOut:
    """Search signups, users, students, circles, support threads, and website inquiries."""
    data = await run_admin_global_search(db, query=q, limit_per_group=limit)
    return AdminSearchOut(**data)
