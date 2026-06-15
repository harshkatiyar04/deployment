from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal import LegalAcceptance, LegalDocument


def _row_to_acceptance_dict(row: LegalAcceptance) -> dict:
    return {
        "id": row.id,
        "signup_request_id": row.signup_request_id,
        "document_id": row.document_id,
        "doc_type": row.doc_type,
        "document_version": row.document_version,
        "document_sha256": row.document_sha256,
        "legal_entity": row.legal_entity,
        "email": row.email,
        "full_name": row.full_name,
        "persona": row.persona,
        "acceptance_method": row.acceptance_method,
        "acceptance_channel": row.acceptance_channel,
        "acceptance_role": row.acceptance_role,
        "ip_address": row.ip_address,
        "forwarded_ip": row.forwarded_ip,
        "user_agent": row.user_agent,
        "accept_locale": row.accept_locale,
        "accepted_at": row.accepted_at.isoformat() if row.accepted_at else None,
        "metadata_json": row.metadata_json or {},
    }


async def build_admin_legal_summary(db: AsyncSession) -> dict:
    total_res = await db.execute(select(func.count()).select_from(LegalAcceptance))
    total = int(total_res.scalar_one() or 0)

    thirty_ago = datetime.now(timezone.utc) - timedelta(days=30)
    thirty_days_res = await db.execute(
        select(func.count())
        .select_from(LegalAcceptance)
        .where(LegalAcceptance.accepted_at >= thirty_ago)
    )
    last_30_days = int(thirty_days_res.scalar_one() or 0)

    signup_res = await db.execute(
        select(func.count())
        .select_from(LegalAcceptance)
        .where(LegalAcceptance.acceptance_channel == "web_signup")
    )
    at_signup = int(signup_res.scalar_one() or 0)

    reaccept_res = await db.execute(
        select(func.count())
        .select_from(LegalAcceptance)
        .where(LegalAcceptance.acceptance_channel == "web_reacceptance")
    )
    reacceptances = int(reaccept_res.scalar_one() or 0)

    active_doc = await db.execute(
        select(LegalDocument)
        .where(LegalDocument.is_active.is_(True), LegalDocument.doc_type == "platform_terms")
        .order_by(LegalDocument.effective_date.desc())
        .limit(1)
    )
    active = active_doc.scalar_one_or_none()

    on_current = 0
    if active:
        on_current_res = await db.execute(
            select(func.count(func.distinct(LegalAcceptance.signup_request_id)))
            .select_from(LegalAcceptance)
            .where(
                LegalAcceptance.doc_type == active.doc_type,
                LegalAcceptance.document_version == active.version,
                LegalAcceptance.signup_request_id.isnot(None),
            )
        )
        on_current = int(on_current_res.scalar_one() or 0)

    return {
        "total_acceptances": total,
        "acceptances_last_30_days": last_30_days,
        "at_signup": at_signup,
        "reacceptances": reacceptances,
        "users_on_current_version": on_current,
        "active_document": {
            "doc_type": active.doc_type,
            "version": active.version,
            "title": active.title,
            "legal_entity": active.legal_entity,
            "effective_date": active.effective_date.isoformat() if active and active.effective_date else None,
            "content_sha256": active.content_sha256 if active else None,
        }
        if active
        else None,
    }


async def list_legal_documents(db: AsyncSession) -> list[dict]:
    res = await db.execute(
        select(LegalDocument).order_by(
            LegalDocument.doc_type.asc(),
            LegalDocument.effective_date.desc(),
            LegalDocument.created_at.desc(),
        )
    )
    rows = res.scalars().all()
    return [
        {
            "id": row.id,
            "doc_type": row.doc_type,
            "version": row.version,
            "title": row.title,
            "legal_entity": row.legal_entity,
            "effective_date": row.effective_date.isoformat() if row.effective_date else None,
            "pdf_path": row.pdf_path,
            "content_sha256": row.content_sha256,
            "is_active": row.is_active,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def _acceptance_filters(
    *,
    search: Optional[str],
    doc_type: Optional[str],
    version: Optional[str],
    persona: Optional[str],
    channel: Optional[str],
):
    clauses = []
    if search:
        q = f"%{search.strip().lower()}%"
        clauses.append(
            or_(
                func.lower(LegalAcceptance.email).like(q),
                func.lower(LegalAcceptance.full_name).like(q),
                cast(LegalAcceptance.signup_request_id, String).ilike(q),
            )
        )
    if doc_type:
        clauses.append(LegalAcceptance.doc_type == doc_type.strip())
    if version:
        clauses.append(LegalAcceptance.document_version == version.strip())
    if persona:
        clauses.append(LegalAcceptance.persona == persona.strip())
    if channel:
        clauses.append(LegalAcceptance.acceptance_channel == channel.strip())
    return clauses


async def list_legal_acceptances(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    doc_type: Optional[str] = None,
    version: Optional[str] = None,
    persona: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    clauses = _acceptance_filters(
        search=search,
        doc_type=doc_type,
        version=version,
        persona=persona,
        channel=channel,
    )

    count_stmt = select(func.count()).select_from(LegalAcceptance)
    list_stmt = select(LegalAcceptance).order_by(LegalAcceptance.accepted_at.desc())
    for clause in clauses:
        count_stmt = count_stmt.where(clause)
        list_stmt = list_stmt.where(clause)

    total_res = await db.execute(count_stmt)
    total = int(total_res.scalar_one() or 0)

    res = await db.execute(list_stmt.limit(limit).offset(offset))
    rows = res.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "acceptances": [_row_to_acceptance_dict(row) for row in rows],
    }


async def get_legal_acceptance(db: AsyncSession, acceptance_id: str) -> Optional[dict]:
    res = await db.execute(select(LegalAcceptance).where(LegalAcceptance.id == acceptance_id).limit(1))
    row = res.scalar_one_or_none()
    if row is None:
        return None
    return _row_to_acceptance_dict(row)


async def list_acceptances_for_signup(db: AsyncSession, signup_id: str) -> list[dict]:
    res = await db.execute(
        select(LegalAcceptance)
        .where(LegalAcceptance.signup_request_id == signup_id)
        .order_by(LegalAcceptance.accepted_at.desc())
    )
    return [_row_to_acceptance_dict(row) for row in res.scalars().all()]
