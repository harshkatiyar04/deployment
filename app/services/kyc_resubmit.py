"""Applicant KYC document resubmit when admin requests additional information."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import KycStatus
from app.models.signup import KycDocument, SignupRequest
from app.services.storage import save_kyc_file


async def list_signup_kyc_documents(db: AsyncSession, signup_id: str) -> list[KycDocument]:
    res = await db.execute(
        select(KycDocument)
        .where(KycDocument.signup_id == signup_id)
        .order_by(KycDocument.created_at.desc())
    )
    return list(res.scalars().all())


async def resubmit_kyc_documents(
    db: AsyncSession,
    signup: SignupRequest,
    files: list[UploadFile],
) -> SignupRequest:
    if signup.kyc_status != KycStatus.info_required:
        raise HTTPException(
            status_code=400,
            detail="Document upload is only available when additional information has been requested.",
        )
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one document.")

    existing_docs_res = await db.execute(
        select(KycDocument).where(KycDocument.signup_id == signup.id)
    )
    existing_docs = {d.original_filename: d for d in existing_docs_res.scalars().all()}

    for f in files:
        original_filename = f.filename or "kyc_document"
        stored_filename, stored_path, content_type = await save_kyc_file(
            signup_id=signup.id,
            file=f,
        )
        old = existing_docs.get(original_filename)
        if old:
            if old.stored_path and not str(old.stored_path).startswith("http"):
                try:
                    Path(old.stored_path).unlink(missing_ok=True)
                except Exception:
                    pass
            old.stored_filename = stored_filename
            old.stored_path = stored_path
            old.content_type = content_type
        else:
            db.add(
                KycDocument(
                    signup_id=signup.id,
                    original_filename=original_filename,
                    stored_filename=stored_filename,
                    stored_path=stored_path,
                    content_type=content_type,
                )
            )

    signup.kyc_status = KycStatus.pending
    signup.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(signup)
    return signup
