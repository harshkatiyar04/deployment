from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import get_current_user
from app.db.session import get_db
from app.models.signup import SignupRequest
from app.services.legal_terms import (
    DOC_TYPE_LABELS,
    DOC_TYPE_PARENT_MEMBER,
    DOC_TYPE_PLATFORM,
    DOC_TYPE_PRIVACY,
    DOC_TYPE_STUDENT,
    LEGAL_ENTITY_NAME,
    enforce_document_acceptance,
    enforce_platform_terms_at_signup,
    get_active_document,
    list_pending_reacceptances,
    parse_terms_accepted,
    user_needs_terms_reacceptance,
)

router = APIRouter(prefix="/legal", tags=["legal"])

PUBLIC_DOC_TYPES = {
    "terms": DOC_TYPE_PLATFORM,
    "privacy": DOC_TYPE_PRIVACY,
    "parent-member": DOC_TYPE_PARENT_MEMBER,
    "student-declaration": DOC_TYPE_STUDENT,
}


class LegalDocumentOut(BaseModel):
    doc_type: str
    version: str
    title: str
    legal_entity: str
    effective_date: date
    pdf_url: str
    content_sha256: str


class TermsAcceptBody(BaseModel):
    terms_version: str
    terms_accepted: bool = True


class LegalAcceptItem(BaseModel):
    doc_type: str
    version: str
    accepted: bool = True


class LegalAcceptBatchBody(BaseModel):
    acceptances: list[LegalAcceptItem] = Field(min_length=1)


class TermsAcceptOut(BaseModel):
    ok: bool
    version: str
    accepted_at: datetime


class PendingLegalDocumentOut(BaseModel):
    doc_type: str
    version: str
    title: str
    legal_entity: str
    effective_date: str
    content_sha256: str


def _absolute_pdf_url(request: Request, pdf_path: str) -> str:
    if pdf_path.startswith("http://") or pdf_path.startswith("https://"):
        return pdf_path
    base = str(request.base_url).rstrip("/")
    return f"{base}{pdf_path}"


def _document_out(request: Request, doc) -> LegalDocumentOut:
    return LegalDocumentOut(
        doc_type=doc.doc_type,
        version=doc.version,
        title=doc.title,
        legal_entity=doc.legal_entity or LEGAL_ENTITY_NAME,
        effective_date=doc.effective_date,
        pdf_url=_absolute_pdf_url(request, doc.pdf_path),
        content_sha256=doc.content_sha256,
    )


@router.get("/terms/current", response_model=LegalDocumentOut)
async def get_current_platform_terms(request: Request, db: AsyncSession = Depends(get_db)):
    doc = await get_active_document(db, DOC_TYPE_PLATFORM)
    if doc is None:
        raise HTTPException(status_code=404, detail="Terms and conditions are not available yet.")
    return _document_out(request, doc)


@router.get("/privacy/current", response_model=LegalDocumentOut)
async def get_current_privacy_policy(request: Request, db: AsyncSession = Depends(get_db)):
    doc = await get_active_document(db, DOC_TYPE_PRIVACY)
    if doc is None:
        raise HTTPException(status_code=404, detail="Privacy policy is not available yet.")
    return _document_out(request, doc)


@router.get("/parent-member/current", response_model=LegalDocumentOut)
async def get_current_parent_member_terms(request: Request, db: AsyncSession = Depends(get_db)):
    doc = await get_active_document(db, DOC_TYPE_PARENT_MEMBER)
    if doc is None:
        raise HTTPException(status_code=404, detail="Parent & member terms are not available yet.")
    return _document_out(request, doc)


@router.get("/student-declaration/current", response_model=LegalDocumentOut)
async def get_current_student_declaration(request: Request, db: AsyncSession = Depends(get_db)):
    doc = await get_active_document(db, DOC_TYPE_STUDENT)
    if doc is None:
        raise HTTPException(status_code=404, detail="Student declaration is not available yet.")
    return _document_out(request, doc)


@router.get("/documents/{slug}/current", response_model=LegalDocumentOut)
async def get_current_document_by_slug(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    doc_type = PUBLIC_DOC_TYPES.get(slug)
    if doc_type is None:
        raise HTTPException(status_code=404, detail="Unknown legal document.")
    doc = await get_active_document(db, doc_type)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document is not available yet.")
    return _document_out(request, doc)


@router.get("/reacceptance-status")
async def terms_reacceptance_status(
    db: AsyncSession = Depends(get_db),
    current_user: SignupRequest = Depends(get_current_user),
):
    pending = await list_pending_reacceptances(db, current_user)
    active_platform = await get_active_document(db, DOC_TYPE_PLATFORM)
    return {
        "reacceptance_required": len(pending) > 0,
        "pending_documents": pending,
        "current_version": active_platform.version if active_platform else None,
        "title": active_platform.title if active_platform else None,
        "legal_entity": active_platform.legal_entity if active_platform else LEGAL_ENTITY_NAME,
    }


@router.post("/terms/accept", response_model=TermsAcceptOut)
async def accept_current_platform_terms(
    body: TermsAcceptBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: SignupRequest = Depends(get_current_user),
):
    if not parse_terms_accepted(body.terms_accepted):
        raise HTTPException(status_code=400, detail="Terms acceptance is required.")
    row = await enforce_platform_terms_at_signup(
        db,
        request,
        current_user,
        body.terms_version,
        body.terms_accepted,
        acceptance_role="self",
    )
    row.acceptance_channel = "web_reacceptance"
    row.acceptance_method = "login_modal_checkbox"
    await db.commit()
    return TermsAcceptOut(ok=True, version=row.document_version, accepted_at=row.accepted_at)


@router.post("/accept-batch")
async def accept_legal_documents_batch(
    body: LegalAcceptBatchBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: SignupRequest = Depends(get_current_user),
):
    rows = []
    for item in body.acceptances:
        if not parse_terms_accepted(item.accepted):
            label = DOC_TYPE_LABELS.get(item.doc_type, item.doc_type)
            raise HTTPException(status_code=400, detail=f"Acceptance required for {label}.")
        row = await enforce_document_acceptance(
            db,
            request,
            current_user,
            item.doc_type,
            item.version,
            item.accepted,
            acceptance_channel="web_reacceptance",
            acceptance_method="login_modal_checkbox",
        )
        rows.append(row)
    await db.commit()
    return {
        "ok": True,
        "accepted": [
            {"doc_type": row.doc_type, "version": row.document_version, "accepted_at": row.accepted_at}
            for row in rows
        ],
    }
