from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_meta import best_client_ip, get_client_ip
from app.models.enums import MemberKind, Persona
from app.models.legal import LegalAcceptance, LegalDocument
from app.models.signup import SignupRequest

LEGAL_ENTITY_NAME = "Zenk Impact India Private Limited"

DOC_TYPE_PLATFORM = "platform_terms"
DOC_TYPE_PRIVACY = "privacy_policy"
DOC_TYPE_PARENT_MEMBER = "parent_member_terms"
DOC_TYPE_STUDENT = "student_declaration"

DOC_TYPE_LABELS = {
    DOC_TYPE_PLATFORM: "Platform Terms & Conditions",
    DOC_TYPE_PRIVACY: "Privacy Policy",
    DOC_TYPE_PARENT_MEMBER: "Parent & Circle Member Terms",
    DOC_TYPE_STUDENT: "Student Participation Declaration",
}


def parse_terms_accepted(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "yes", "on"}


def required_doc_types_for_signup(persona: Persona, *, is_parent_guardian: bool = False) -> list[str]:
    types = [DOC_TYPE_PLATFORM, DOC_TYPE_PRIVACY]
    if persona == Persona.student:
        types.append(DOC_TYPE_STUDENT)
    if persona == Persona.sponsor_member and is_parent_guardian:
        types.append(DOC_TYPE_PARENT_MEMBER)
    return types


def required_doc_types_for_user(signup: SignupRequest) -> list[str]:
    persona = signup.persona
    is_parent = (
        persona == Persona.sponsor_member
        and signup.member_kind == MemberKind.parent_guardian.value
    )
    return required_doc_types_for_signup(persona, is_parent_guardian=is_parent)


async def get_active_document(db: AsyncSession, doc_type: str) -> Optional[LegalDocument]:
    res = await db.execute(
        select(LegalDocument)
        .where(LegalDocument.doc_type == doc_type, LegalDocument.is_active.is_(True))
        .order_by(LegalDocument.effective_date.desc(), LegalDocument.created_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def require_active_document(db: AsyncSession, doc_type: str, version: str) -> LegalDocument:
    label = DOC_TYPE_LABELS.get(doc_type, "Legal document")
    doc = await get_active_document(db, doc_type)
    if doc is None:
        raise HTTPException(
            status_code=503,
            detail=f"{label} is not configured. Please try again later.",
        )
    if doc.version != version.strip():
        raise HTTPException(
            status_code=400,
            detail=f"{label} version mismatch. Please refresh and accept version {doc.version}.",
        )
    return doc


async def get_latest_acceptance(
    db: AsyncSession,
    signup_id: str,
    doc_type: str,
) -> Optional[LegalAcceptance]:
    res = await db.execute(
        select(LegalAcceptance)
        .where(
            LegalAcceptance.signup_request_id == signup_id,
            LegalAcceptance.doc_type == doc_type,
        )
        .order_by(LegalAcceptance.accepted_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def record_terms_acceptance(
    db: AsyncSession,
    *,
    request: Request,
    signup: SignupRequest,
    document: LegalDocument,
    acceptance_role: str = "self",
    acceptance_channel: str = "web_signup",
    acceptance_method: str = "signup_checkbox",
    extra_metadata: Optional[dict] = None,
) -> LegalAcceptance:
    direct_ip, forwarded_ip = get_client_ip(request)
    row = LegalAcceptance(
        id=str(uuid4()),
        signup_request_id=signup.id,
        document_id=document.id,
        doc_type=document.doc_type,
        document_version=document.version,
        document_sha256=document.content_sha256,
        legal_entity=document.legal_entity,
        email=(signup.email or "").strip().lower(),
        full_name=signup.full_name,
        persona=str(signup.persona.value if hasattr(signup.persona, "value") else signup.persona),
        acceptance_method=acceptance_method,
        acceptance_channel=acceptance_channel,
        acceptance_role=acceptance_role,
        ip_address=best_client_ip(request),
        forwarded_ip=forwarded_ip,
        user_agent=request.headers.get("user-agent"),
        accept_locale=request.headers.get("accept-language", "")[:20] or None,
        accepted_at=datetime.now(timezone.utc),
        metadata_json={
            "direct_ip": direct_ip,
            **(extra_metadata or {}),
        },
    )
    db.add(row)
    return row


async def enforce_document_acceptance(
    db: AsyncSession,
    request: Request,
    signup: SignupRequest,
    doc_type: str,
    version: str,
    accepted: object,
    *,
    acceptance_role: str = "self",
    acceptance_channel: str = "web_signup",
    acceptance_method: str = "signup_checkbox",
) -> LegalAcceptance:
    label = DOC_TYPE_LABELS.get(doc_type, "Legal document")
    if not parse_terms_accepted(accepted):
        raise HTTPException(status_code=400, detail=f"You must accept the {label} to register.")
    document = await require_active_document(db, doc_type, version)
    return await record_terms_acceptance(
        db,
        request=request,
        signup=signup,
        document=document,
        acceptance_role=acceptance_role,
        acceptance_channel=acceptance_channel,
        acceptance_method=acceptance_method,
    )


async def enforce_signup_legal_bundle(
    db: AsyncSession,
    request: Request,
    signup: SignupRequest,
    *,
    terms_version: str,
    terms_accepted: object,
    privacy_version: str,
    privacy_accepted: object,
    parent_member_version: Optional[str] = None,
    parent_member_accepted: Optional[object] = None,
    student_declaration_version: Optional[str] = None,
    student_declaration_accepted: Optional[object] = None,
    acceptance_role: str = "self",
) -> list[LegalAcceptance]:
    rows: list[LegalAcceptance] = []
    rows.append(
        await enforce_document_acceptance(
            db, request, signup, DOC_TYPE_PLATFORM, terms_version, terms_accepted,
            acceptance_role=acceptance_role,
        )
    )
    rows.append(
        await enforce_document_acceptance(
            db, request, signup, DOC_TYPE_PRIVACY, privacy_version, privacy_accepted,
            acceptance_role=acceptance_role,
        )
    )
    if parent_member_version:
        rows.append(
            await enforce_document_acceptance(
                db,
                request,
                signup,
                DOC_TYPE_PARENT_MEMBER,
                parent_member_version,
                parent_member_accepted,
                acceptance_role=acceptance_role,
            )
        )
    if student_declaration_version:
        rows.append(
            await enforce_document_acceptance(
                db,
                request,
                signup,
                DOC_TYPE_STUDENT,
                student_declaration_version,
                student_declaration_accepted,
                acceptance_role=acceptance_role,
            )
        )
    return rows


async def enforce_platform_terms_at_signup(
    db: AsyncSession,
    request: Request,
    signup: SignupRequest,
    terms_version: str,
    terms_accepted: object,
    *,
    acceptance_role: str = "self",
) -> LegalAcceptance:
    return await enforce_document_acceptance(
        db,
        request,
        signup,
        DOC_TYPE_PLATFORM,
        terms_version,
        terms_accepted,
        acceptance_role=acceptance_role,
    )


async def list_pending_reacceptances(db: AsyncSession, signup: SignupRequest) -> list[dict]:
    pending: list[dict] = []
    for doc_type in required_doc_types_for_user(signup):
        active = await get_active_document(db, doc_type)
        if active is None:
            continue
        latest = await get_latest_acceptance(db, signup.id, doc_type)
        if latest is None or latest.document_version != active.version:
            pending.append(
                {
                    "doc_type": active.doc_type,
                    "version": active.version,
                    "title": active.title,
                    "legal_entity": active.legal_entity,
                    "effective_date": active.effective_date.isoformat(),
                    "content_sha256": active.content_sha256,
                }
            )
    return pending


async def user_needs_terms_reacceptance(db: AsyncSession, signup_id: str) -> tuple[bool, Optional[str]]:
    res = await db.execute(select(SignupRequest).where(SignupRequest.id == signup_id).limit(1))
    signup = res.scalar_one_or_none()
    if signup is None:
        return False, None
    pending = await list_pending_reacceptances(db, signup)
    if not pending:
        platform = await get_active_document(db, DOC_TYPE_PLATFORM)
        return False, platform.version if platform else None
    platform_pending = next((p for p in pending if p["doc_type"] == DOC_TYPE_PLATFORM), None)
    version = platform_pending["version"] if platform_pending else pending[0]["version"]
    return True, version


async def user_needs_legal_reacceptance(db: AsyncSession, signup: SignupRequest) -> bool:
    return bool(await list_pending_reacceptances(db, signup))
