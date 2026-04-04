from datetime import datetime
from pathlib import Path
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.settings import settings
from app.db.session import get_db
from app.models.enums import KycStatus
from app.models.enums import Persona
from app.models.signup import KycDocument, SignupRequest
from app.schemas.signup import (
    AdminDecisionRequest,
    AdminSignupListItem,
    KycDocumentOut,
    KycDocumentView,
)
from app.services.email import send_email
from app.services.email_templates import render_user_approval_html
from app.services.notifications import notify_user_kyc_approved, notify_user_kyc_rejected


router = APIRouter(prefix="/admin/kyc", tags=["admin-kyc"])
logger = logging.getLogger(__name__)


@router.get("/pending", response_model=list[AdminSignupListItem])
async def list_pending(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(SignupRequest)
        .options(selectinload(SignupRequest.documents))
        .where(SignupRequest.kyc_status == KycStatus.pending)
    )
    rows = res.scalars().all()
    return [
        AdminSignupListItem(
            id=r.id,
            persona=r.persona,
            full_name=r.full_name,
            mobile=r.mobile,
            email=r.email,
            kyc_status=r.kyc_status,
            created_at=r.created_at.isoformat() if r.created_at else None,
            documents_count=len(r.documents),
            documents=[
                KycDocumentOut(
                    id=d.id,
                    original_filename=d.original_filename,
                    stored_filename=d.stored_filename,
                    created_at=d.created_at.isoformat() if d.created_at else None,
                )
                for d in r.documents
            ],
        )
        for r in rows
    ]


@router.get("/{signup_id}/documents", response_model=list[KycDocumentOut])
async def list_documents(signup_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(KycDocument).where(KycDocument.signup_id == signup_id))
    docs = res.scalars().all()
    return [
        KycDocumentOut(
            id=d.id,
            original_filename=d.original_filename,
            stored_filename=d.stored_filename,
            created_at=d.created_at.isoformat() if d.created_at else None,
        )
        for d in docs
    ]


@router.get("/documents/{doc_id}")
async def preview_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """
    Preview document in browser (inline display, not download).
    
    Use this URL in <img>, <iframe>, or <embed> tags to display the document.
    """
    res = await db.execute(select(KycDocument).where(KycDocument.id == doc_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="KYC document not found")

    path = Path(doc.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="KYC document missing on disk")

    # Read file content
    with path.open("rb") as f:
        file_content = f.read()
    
    # Return with inline Content-Disposition for browser preview
    media_type = doc.content_type or "application/octet-stream"
    headers = {
        "Content-Disposition": f'inline; filename="{doc.original_filename or path.name}"',
        "Content-Type": media_type,
    }
    
    return Response(content=file_content, headers=headers, media_type=media_type)


@router.get("/documents/{doc_id}/view", response_model=KycDocumentView)
async def view_document_base64(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Get KYC document preview URL for UI viewing."""
    res = await db.execute(select(KycDocument).where(KycDocument.id == doc_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="KYC document not found")

    path = Path(doc.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="KYC document missing on disk")

    # Return preview URL instead of base64
    preview_url = f"/admin/kyc/documents/{doc_id}"
    
    return KycDocumentView(
        id=doc.id,
        original_filename=doc.original_filename,
        preview_url=preview_url,
        content_type=doc.content_type,
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )


@router.get("/{signup_id}/documents/view", response_model=list[KycDocumentView])
async def view_all_documents_base64(signup_id: str, db: AsyncSession = Depends(get_db)):
    """Get all KYC documents preview URLs for a signup (for UI viewing)."""
    # First verify signup exists
    signup_res = await db.execute(select(SignupRequest).where(SignupRequest.id == signup_id))
    signup = signup_res.scalar_one_or_none()
    if not signup:
        raise HTTPException(status_code=404, detail="Signup not found")
    
    # Get documents for this signup
    res = await db.execute(select(KycDocument).where(KycDocument.signup_id == signup_id))
    docs = res.scalars().all()
    
    # Return professional message if no documents
    if not docs:
        raise HTTPException(
            status_code=404,
            detail="No KYC documents available for preview. This signup has not uploaded any documents yet."
        )

    result = []
    for doc in docs:
        path = Path(doc.stored_path)
        if not path.exists():
            logger.warning("Document file missing on disk: %s", doc.stored_path)
            continue

        # Return preview URL instead of base64
        preview_url = f"/admin/kyc/documents/{doc.id}"
        
        result.append(
            KycDocumentView(
                id=doc.id,
                original_filename=doc.original_filename,
                preview_url=preview_url,
                content_type=doc.content_type,
                created_at=doc.created_at.isoformat() if doc.created_at else None,
            )
        )

    # If all documents failed to read, return message
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No KYC documents available for preview. Document files are missing or cannot be accessed."
        )

    return result


@router.post("/{signup_id}/decision")
async def decide(signup_id: str, body: AdminDecisionRequest, db: AsyncSession = Depends(get_db)):
    if body.decision not in {KycStatus.approved, KycStatus.rejected}:
        raise HTTPException(status_code=400, detail="Decision must be approved or rejected")

    res = await db.execute(select(SignupRequest).where(SignupRequest.id == signup_id))
    signup = res.scalar_one_or_none()
    if not signup:
        raise HTTPException(status_code=404, detail="Signup not found")

    signup.kyc_status = body.decision
    signup.admin_note = body.note
    signup.updated_at = datetime.utcnow()
    await db.commit()

    # Notify user via email and in-app notification
    persona_labels = {
        Persona.sponsor: "Sponsor",
        Persona.vendor: "Vendor",
        Persona.student: "Student",
    }
    label = persona_labels.get(signup.persona, "User")
    
    if signup.kyc_status == KycStatus.approved:
        # Email notification
        subject = f"Your Zenk {label} KYC is Approved"
        text_body = (
            f"Hello {signup.full_name},\n\n"
            f"Your {label} registration on Zenk has been approved.\n\n"
            f"Please login to Zenk ({settings.website_url}) with your password.\n\n"
            "Regards,\n"
            "Zenk Team\n"
        )
        html_body = render_user_approval_html(
            full_name=signup.full_name,
            persona_label=label,
            website_url=settings.website_url,
        )
        try:
            await send_email(
                subject=subject,
                to_email=signup.email,
                text_body=text_body,
                html_body=html_body,
            )
        except Exception:
            # Don't fail admin decision if email sending fails
            logger.exception("Failed to send approval email for signup_id=%s", signup.id)
        
        # In-app notification
        try:
            await notify_user_kyc_approved(
                signup_id=signup.id,
                full_name=signup.full_name,
                persona=label.lower(),
                db=db,
            )
        except Exception:
            logger.exception("Failed to create approval notification for signup_id=%s", signup.id)
    
    elif signup.kyc_status == KycStatus.rejected:
        # In-app notification for rejection
        try:
            await notify_user_kyc_rejected(
                signup_id=signup.id,
                full_name=signup.full_name,
                persona=label.lower(),
                admin_note=body.note,
                db=db,
            )
        except Exception:
            logger.exception("Failed to create rejection notification for signup_id=%s", signup.id)

    return {"id": signup.id, "kyc_status": signup.kyc_status, "note": signup.admin_note}


