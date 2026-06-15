"""Admin legal registry — terms acceptances audit log."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.services.admin_legal_registry import (
    build_admin_legal_summary,
    get_legal_acceptance,
    list_acceptances_for_signup,
    list_legal_acceptances,
    list_legal_documents,
)

router = APIRouter(
    prefix="/admin/legal",
    tags=["admin-legal"],
    dependencies=[Depends(require_admin_api_key)],
)


class LegalAcceptanceOut(BaseModel):
    id: str
    signup_request_id: Optional[str] = None
    document_id: str
    doc_type: str
    document_version: str
    document_sha256: str
    legal_entity: str
    email: str
    full_name: str
    persona: str
    acceptance_method: str
    acceptance_channel: str
    acceptance_role: str
    ip_address: Optional[str] = None
    forwarded_ip: Optional[str] = None
    user_agent: Optional[str] = None
    accept_locale: Optional[str] = None
    accepted_at: Optional[str] = None
    metadata_json: dict = {}


class LegalAcceptancesPageOut(BaseModel):
    total: int
    limit: int
    offset: int
    acceptances: list[LegalAcceptanceOut]


class LegalDocumentOut(BaseModel):
    id: str
    doc_type: str
    version: str
    title: str
    legal_entity: str
    effective_date: Optional[str] = None
    pdf_path: str
    content_sha256: str
    is_active: bool
    created_at: Optional[str] = None


class ActiveDocumentSummary(BaseModel):
    doc_type: str
    version: str
    title: str
    legal_entity: str
    effective_date: Optional[str] = None
    content_sha256: Optional[str] = None


class LegalSummaryOut(BaseModel):
    total_acceptances: int
    acceptances_last_30_days: int
    at_signup: int
    reacceptances: int
    users_on_current_version: int
    active_document: Optional[ActiveDocumentSummary] = None


@router.get("/summary", response_model=LegalSummaryOut)
async def admin_legal_summary(db: AsyncSession = Depends(get_db)):
    return LegalSummaryOut(**await build_admin_legal_summary(db))


@router.get("/documents", response_model=list[LegalDocumentOut])
async def admin_legal_documents(db: AsyncSession = Depends(get_db)):
    return [LegalDocumentOut(**row) for row in await list_legal_documents(db)]


@router.get("/acceptances", response_model=LegalAcceptancesPageOut)
async def admin_legal_acceptances(
    search: Optional[str] = Query(None, max_length=200),
    doc_type: Optional[str] = Query(None),
    version: Optional[str] = Query(None),
    persona: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    data = await list_legal_acceptances(
        db,
        search=search,
        doc_type=doc_type,
        version=version,
        persona=persona,
        channel=channel,
        limit=limit,
        offset=offset,
    )
    return LegalAcceptancesPageOut(**data)


@router.get("/acceptances/by-signup/{signup_id}", response_model=list[LegalAcceptanceOut])
async def admin_legal_acceptances_for_signup(
    signup_id: str,
    db: AsyncSession = Depends(get_db),
):
    rows = await list_acceptances_for_signup(db, signup_id)
    return [LegalAcceptanceOut(**row) for row in rows]


@router.get("/acceptances/{acceptance_id}", response_model=LegalAcceptanceOut)
async def admin_legal_acceptance_detail(
    acceptance_id: str,
    db: AsyncSession = Depends(get_db),
):
    row = await get_legal_acceptance(db, acceptance_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Acceptance record not found.")
    return LegalAcceptanceOut(**row)
