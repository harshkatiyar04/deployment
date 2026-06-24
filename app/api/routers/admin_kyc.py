from datetime import datetime
from pathlib import Path
import logging

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.admin_deps import require_admin_api_key
from app.core.settings import settings
from app.core.signup_locales import build_contact_display
from app.db.session import get_db
from app.models.enums import KycStatus, MemberKind
from app.models.enums import Persona
from app.models.signup import KycDocument, SignupRequest
from app.models.student_family import StudentFamilyLink
from app.schemas.signup import (
    AdminDecisionRequest,
    AdminSignupListItem,
    FullSignupDetails,
    KycDocumentOut,
    KycDocumentView,
    LinkedSignupSummary,
    SignupContactDisplay,
)
from app.services.email import send_email
from app.services.email_templates import render_user_approval_html
from app.services.kyc_review import extract_kyc_review_note
from app.services.notifications import (
    notify_user_kyc_approved,
    notify_user_kyc_info_required,
    notify_user_kyc_rejected,
)
from app.services.school_provision import ensure_school_profile
from app.services.cloudinary_service import fetch_cloudinary_bytes


router = APIRouter(
    prefix="/admin/kyc",
    tags=["admin-kyc"],
    dependencies=[Depends(require_admin_api_key)],
)
logger = logging.getLogger(__name__)

PERSONA_LABELS = {
    Persona.sponsor: "Sponsor",
    Persona.sponsor_leader: "Sponsor Leader",
    Persona.sponsor_member: "Sponsor Member",
    Persona.vendor: "Vendor",
    Persona.student: "Student",
    Persona.corporate: "Corporate",
    Persona.mentor: "Mentor",
    Persona.school: "School",
}

PRIMARY_SIGNUP_PERSONAS = {Persona.sponsor, Persona.vendor, Persona.student}


def _display_role(signup: SignupRequest) -> str:
    if signup.persona == Persona.student:
        return "Student"
    if signup.persona == Persona.sponsor_member and signup.member_kind == MemberKind.parent_guardian.value:
        return "Parent / guardian"
    if signup.persona == Persona.sponsor_member:
        return "Circle member"
    return PERSONA_LABELS.get(signup.persona, signup.persona.value)


def _linked_summary(signup: SignupRequest) -> LinkedSignupSummary:
    return LinkedSignupSummary(
        id=signup.id,
        full_name=signup.full_name,
        kyc_status=signup.kyc_status,
        member_kind=signup.member_kind,
        documents_count=len(signup.documents),
    )


async def _family_links_for_signup(db: AsyncSession, signup: SignupRequest) -> tuple[SignupRequest | None, SignupRequest | None]:
    """Return (linked_guardian, linked_student) for admin detail view."""
    guardian: SignupRequest | None = None
    student: SignupRequest | None = None

    if signup.persona == Persona.student:
        link_res = await db.execute(
            select(StudentFamilyLink).where(StudentFamilyLink.student_signup_id == signup.id)
        )
        link = link_res.scalar_one_or_none()
        if link:
            g_res = await db.execute(
                select(SignupRequest)
                .options(selectinload(SignupRequest.documents))
                .where(SignupRequest.id == link.parent_signup_id)
            )
            guardian = g_res.scalar_one_or_none()
    elif signup.member_kind == MemberKind.parent_guardian.value and signup.linked_student_signup_id:
        s_res = await db.execute(
            select(SignupRequest)
            .options(selectinload(SignupRequest.documents))
            .where(SignupRequest.id == signup.linked_student_signup_id)
        )
        student = s_res.scalar_one_or_none()

    return guardian, student


def _normalize_stored_path(stored_path: str | None) -> str:
    return (stored_path or "").strip()


def _is_remote_storage(stored_path: str | None) -> bool:
    s = _normalize_stored_path(stored_path)
    if not s:
        return False
    lower = s.lower()
    return (
        lower.startswith("http://")
        or lower.startswith("https://")
        or "cloudinary.com" in lower
        or "res.cloudinary.com" in lower
    )


def _infer_content_type(doc: KycDocument) -> str | None:
    if doc.content_type:
        return doc.content_type
    name = (doc.original_filename or doc.stored_filename or "").lower()
    path = (doc.stored_path or "").lower()
    for ext, mime in (
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".png", "image/png"),
        (".webp", "image/webp"),
        (".gif", "image/gif"),
        (".pdf", "application/pdf"),
    ):
        if name.endswith(ext) or ext.lstrip(".") in path:
            return mime
    if "/image/upload/" in path:
        return "image/jpeg"
    return None


def _cloudinary_delivery_url(stored: str, doc: KycDocument) -> str:
    """
    Cloudinary raw assets omit file extensions; mobile browsers often download them
    when embedded. Append a suffix so delivery uses the correct MIME type.
    """
    url = stored.rstrip("/")
    if "/raw/upload/" not in url.lower():
        return stored

    lower = url.lower().split("?")[0]
    if any(lower.endswith(ext) for ext in (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".gif")):
        return stored

    mime = _infer_content_type(doc)
    suffix_by_mime = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    suffix = suffix_by_mime.get(mime or "")
    if not suffix:
        return stored
    query = ""
    if "?" in stored:
        base, query = stored.split("?", 1)
        query = f"?{query}"
        url = base.rstrip("/")
    return f"{url}{suffix}{query}"


def _preview_url_for_doc(doc: KycDocument) -> str:
    path = _normalize_stored_path(doc.stored_path)
    mime = _infer_content_type(doc)
    if _is_remote_storage(path) and mime != "application/pdf":
        return _cloudinary_delivery_url(path, doc)
    return f"/admin/kyc/documents/{doc.id}"


def _doc_view(doc: KycDocument) -> KycDocumentView:
    return KycDocumentView(
        id=doc.id,
        original_filename=doc.original_filename,
        preview_url=_preview_url_for_doc(doc),
        content_type=_infer_content_type(doc),
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )


def _doc_out(d: KycDocument) -> KycDocumentOut:
    return KycDocumentOut(
        id=d.id,
        original_filename=d.original_filename,
        stored_filename=d.stored_filename,
        created_at=d.created_at.isoformat() if d.created_at else None,
    )


def _contact_display_for_signup(r: SignupRequest) -> SignupContactDisplay:
    return SignupContactDisplay(**build_contact_display(
        mobile=r.mobile,
        guardian_mobile=r.guardian_mobile,
        country=r.country,
        pincode=r.pincode,
    ))


def _signup_list_item(r: SignupRequest) -> AdminSignupListItem:
    contact = build_contact_display(mobile=r.mobile, country=r.country, pincode=r.pincode)
    return AdminSignupListItem(
        id=r.id,
        persona=r.persona,
        full_name=r.full_name,
        mobile=r.mobile,
        mobile_display=contact["mobile_display"],
        country_label=contact["country_label"],
        email=r.email,
        kyc_status=r.kyc_status,
        created_at=r.created_at.isoformat() if r.created_at else None,
        documents_count=len(r.documents),
        documents=[_doc_out(d) for d in r.documents],
        member_kind=r.member_kind,
        linked_student_signup_id=r.linked_student_signup_id,
        onboarding_version=r.onboarding_version,
        display_role=_display_role(r),
    )


def _signup_full_details(r: SignupRequest) -> FullSignupDetails:
    return FullSignupDetails(
        id=r.id,
        persona=r.persona,
        kyc_status=r.kyc_status,
        admin_note=r.admin_note,
        created_at=r.created_at.isoformat() if r.created_at else None,
        updated_at=r.updated_at.isoformat() if r.updated_at else None,
        full_name=r.full_name,
        mobile=r.mobile,
        email=r.email,
        address_line1=r.address_line1,
        address_line2=r.address_line2,
        city=r.city,
        state=r.state,
        pincode=r.pincode,
        country=r.country,
        contact_display=_contact_display_for_signup(r),
        sponsor_type=r.sponsor_type,
        pan_number=r.pan_number,
        company_name=r.company_name,
        company_registration_number=r.company_registration_number,
        gst_number=r.gst_number,
        authorized_signatory_name=r.authorized_signatory_name,
        authorized_signatory_designation=r.authorized_signatory_designation,
        business_name=r.business_name,
        business_type=r.business_type,
        product_categories=r.product_categories,
        website=r.website,
        school_name=r.school_name,
        school_principal_name=r.school_principal_name,
        school_affiliation=r.school_affiliation,
        school_affiliation_number=r.school_affiliation_number,
        school_enrollment_year=r.school_enrollment_year,
        date_of_birth=r.date_of_birth.isoformat() if r.date_of_birth else None,
        school_or_college_name=r.school_or_college_name,
        selected_school_id=r.selected_school_id,
        grade_or_year=r.grade_or_year,
        guardian_name=r.guardian_name,
        guardian_mobile=r.guardian_mobile,
        guardian_relationship=r.guardian_relationship,
        login_access_tier=r.login_access_tier,
        member_kind=r.member_kind,
        linked_student_signup_id=r.linked_student_signup_id,
        onboarding_version=r.onboarding_version,
        documents=[_doc_out(d) for d in r.documents],
    )


def _parse_status_filter(status: Optional[str]) -> Optional[KycStatus]:
    if not status or status == "all":
        return None
    try:
        return KycStatus(status)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="status must be pending, approved, rejected, info_required, or all",
        ) from exc


@router.get("/summary")
async def signup_summary(db: AsyncSession = Depends(get_db)):
    """Counts per persona and KYC status for admin queue badges."""
    res = await db.execute(
        select(SignupRequest.persona, SignupRequest.member_kind, SignupRequest.kyc_status, func.count())
        .group_by(SignupRequest.persona, SignupRequest.member_kind, SignupRequest.kyc_status)
    )
    by_persona: dict[str, dict[str, int]] = {}
    totals = {"pending": 0, "approved": 0, "rejected": 0, "info_required": 0, "all": 0}
    for persona, member_kind, kyc_status, count in res.all():
        key = persona.value if hasattr(persona, "value") else str(persona)
        by_persona.setdefault(
            key,
            {"pending": 0, "approved": 0, "rejected": 0, "info_required": 0, "all": 0},
        )
        status_key = kyc_status.value if hasattr(kyc_status, "value") else str(kyc_status)
        by_persona[key][status_key] = by_persona[key].get(status_key, 0) + count
        by_persona[key]["all"] += count
        if key == Persona.sponsor_member.value:
            if member_kind == MemberKind.parent_guardian.value:
                sub_key = f"parent_guardian_{status_key}"
                by_persona[key][sub_key] = by_persona[key].get(sub_key, 0) + count
                if status_key == "pending":
                    by_persona[key]["parent_guardian_pending"] = by_persona[key].get("parent_guardian_pending", 0) + count
            elif member_kind in (None, MemberKind.standard.value):
                sub_key = f"circle_member_{status_key}"
                by_persona[key][sub_key] = by_persona[key].get(sub_key, 0) + count
                if status_key == "pending":
                    by_persona[key]["circle_member_pending"] = by_persona[key].get("circle_member_pending", 0) + count
        if status_key in totals:
            totals[status_key] += count
        totals["all"] += count
    return {"by_persona": by_persona, "totals": totals}


@router.get("/requests", response_model=list[AdminSignupListItem])
async def list_requests(
    persona: Optional[Persona] = Query(None),
    status: Optional[str] = Query("pending", description="pending | approved | rejected | all"),
    persona_group: Optional[str] = Query(
        None,
        description="signup = sponsor+vendor+student; other = all remaining personas",
    ),
    member_kind: Optional[str] = Query(
        None,
        description="parent_guardian | circle_member — narrows sponsor_member queue",
    ),
    db: AsyncSession = Depends(get_db),
):
    """All signup requests for admin review, filterable by persona and KYC status."""
    kyc_filter = _parse_status_filter(status)
    q = select(SignupRequest).options(selectinload(SignupRequest.documents))
    if persona:
        q = q.where(SignupRequest.persona == persona)
        if persona == Persona.sponsor_member:
            if member_kind == MemberKind.parent_guardian.value:
                q = q.where(SignupRequest.member_kind == MemberKind.parent_guardian.value)
            elif member_kind == "circle_member":
                q = q.where(
                    (SignupRequest.member_kind.is_(None))
                    | (SignupRequest.member_kind == MemberKind.standard.value)
                )
    elif persona_group == "signup":
        q = q.where(SignupRequest.persona.in_(PRIMARY_SIGNUP_PERSONAS))
    elif persona_group == "other":
        q = q.where(SignupRequest.persona.not_in(PRIMARY_SIGNUP_PERSONAS))
    if kyc_filter is not None:
        q = q.where(SignupRequest.kyc_status == kyc_filter)
    q = q.order_by(SignupRequest.created_at.desc())
    res = await db.execute(q)
    return [_signup_list_item(r) for r in res.scalars().all()]


@router.get("/pending", response_model=list[AdminSignupListItem])
async def list_pending(db: AsyncSession = Depends(get_db)):
    return await list_requests(status="pending", persona=None, persona_group=None, db=db)


@router.get("/{signup_id}", response_model=FullSignupDetails)
async def get_signup_detail(signup_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(SignupRequest)
        .options(selectinload(SignupRequest.documents))
        .where(SignupRequest.id == signup_id)
    )
    signup = res.scalar_one_or_none()
    if not signup:
        raise HTTPException(status_code=404, detail="Signup not found")
    details = _signup_full_details(signup)
    guardian, student = await _family_links_for_signup(db, signup)
    return details.model_copy(
        update={
            "linked_guardian": _linked_summary(guardian) if guardian else None,
            "linked_student": _linked_summary(student) if student else None,
        }
    )


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
async def preview_document(
    doc_id: str,
    download: bool = Query(False, description="Force download attachment instead of inline view"),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream KYC document with correct MIME headers.
    Proxies Cloudinary raw/PDF assets so browsers open valid PDFs (admin auth required).
    """
    res = await db.execute(select(KycDocument).where(KycDocument.id == doc_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="KYC document not found")

    stored = _normalize_stored_path(doc.stored_path)
    filename = doc.original_filename or "kyc-document"
    media_type = _infer_content_type(doc) or "application/octet-stream"
    if media_type == "application/octet-stream" and filename.lower().endswith(".pdf"):
        media_type = "application/pdf"
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"

    disposition = "attachment" if download else "inline"

    if _is_remote_storage(stored):
        format_hint = None
        if media_type == "application/pdf" or filename.lower().endswith(".pdf"):
            format_hint = "pdf"
        try:
            file_content = await fetch_cloudinary_bytes(stored, format_hint=format_hint)
        except ValueError as exc:
            logger.warning("Cloudinary fetch failed for doc %s: %s", doc_id, exc)
            detail = str(exc) if "not found" in str(exc).lower() else "Could not retrieve document from storage."
            status = 404 if "not found" in str(exc).lower() else 502
            raise HTTPException(status_code=status, detail=detail) from exc

        headers = {
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        }
        return Response(content=file_content, media_type=media_type, headers=headers)

    path = Path(stored)
    if not path.exists():
        raise HTTPException(status_code=404, detail="KYC document missing on disk")

    with path.open("rb") as f:
        file_content = f.read()

    headers = {
        "Content-Disposition": f'{disposition}; filename="{filename}"',
        "Cache-Control": "private, max-age=300",
    }

    return Response(content=file_content, headers=headers, media_type=media_type)


@router.get("/documents/{doc_id}/view", response_model=KycDocumentView)
async def view_document_base64(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Get KYC document preview URL for UI viewing."""
    res = await db.execute(select(KycDocument).where(KycDocument.id == doc_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="KYC document not found")

    stored = _normalize_stored_path(doc.stored_path)
    if not _is_remote_storage(stored):
        path = Path(stored)
        if not path.exists():
            raise HTTPException(status_code=404, detail="KYC document missing on disk")

    return _doc_view(doc)


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
        stored = _normalize_stored_path(doc.stored_path)
        if _is_remote_storage(stored):
            result.append(_doc_view(doc))
            continue
        path = Path(stored)
        if not path.exists():
            logger.warning("KYC file missing on disk (not a remote URL): %s", stored)
            continue
        result.append(_doc_view(doc))

    # If all documents failed to read, return message
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No KYC documents available for preview. Document files are missing or cannot be accessed."
        )

    return result


@router.post("/{signup_id}/decision")
async def decide(signup_id: str, body: AdminDecisionRequest, db: AsyncSession = Depends(get_db)):
    allowed = {KycStatus.approved, KycStatus.rejected, KycStatus.info_required}
    if body.decision not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Decision must be approved, rejected, or info_required",
        )

    note = (body.note or "").strip()
    if body.decision in {KycStatus.rejected, KycStatus.info_required} and not note:
        raise HTTPException(
            status_code=400,
            detail="A comment is required when rejecting or requesting additional information.",
        )

    res = await db.execute(select(SignupRequest).where(SignupRequest.id == signup_id))
    signup = res.scalar_one_or_none()
    if not signup:
        raise HTTPException(status_code=404, detail="Signup not found")

    if signup.kyc_status != KycStatus.pending:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot decide on signup with status '{signup.kyc_status.value}'.",
        )

    from app.services.circle_member_invite import merge_admin_kyc_note

    signup.kyc_status = body.decision
    signup.admin_note = merge_admin_kyc_note(signup.admin_note, note or body.note)
    signup.updated_at = datetime.utcnow()

    if body.decision == KycStatus.approved and signup.persona == Persona.school:
        await ensure_school_profile(db, signup, is_partner=True, onboarding_source="public_signup")

    await db.commit()

    # Notify user via email and in-app notification
    label = PERSONA_LABELS.get(signup.persona, "User")
    
    if signup.kyc_status == KycStatus.approved:
        if signup.persona == Persona.sponsor_member and signup.member_kind == MemberKind.parent_guardian.value:
            label = "Parent / guardian"
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
        try:
            await notify_user_kyc_rejected(
                signup_id=signup.id,
                full_name=signup.full_name,
                persona=label.lower(),
                admin_note=extract_kyc_review_note(signup.admin_note),
                db=db,
            )
        except Exception:
            logger.exception("Failed to create rejection notification for signup_id=%s", signup.id)

    elif signup.kyc_status == KycStatus.info_required:
        try:
            await notify_user_kyc_info_required(
                signup_id=signup.id,
                full_name=signup.full_name,
                persona=label.lower(),
                admin_note=extract_kyc_review_note(signup.admin_note),
                db=db,
            )
        except Exception:
            logger.exception(
                "Failed to create info_required notification for signup_id=%s",
                signup.id,
            )

    return {
        "id": signup.id,
        "kyc_status": signup.kyc_status,
        "note": signup.admin_note,
        "review_note": extract_kyc_review_note(signup.admin_note),
    }


