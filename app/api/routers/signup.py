from datetime import date, datetime
from pathlib import Path
from typing import Optional
import logging
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.enums import KycStatus, Persona
from app.models.signup import KycDocument, SignupRequest
from app.schemas.signup import SignupResponse, FullSignupDetails, StudentFamilySignupResponse
from app.services.student_family import (
    compute_login_access_tier,
    create_parent_guardian_signup,
    upsert_family_link,
)
from app.core.settings import settings
from app.core.security import hash_password
from app.core.signup_locales import (
    validate_and_normalize_mobile,
    validate_signup_contact_address,
)
from app.services.email import send_email
from app.core.signup_locales import format_mobile_display
from app.services.email_templates import render_admin_notification_html
from app.services.notifications import notify_admin_new_signup, notify_circle_leaders_member_application
from app.services.storage import save_kyc_file
from app.services.student_onboarding_v2 import (
    ONBOARDING_V2,
    create_school_interest,
    list_public_schools,
)
from app.services.school_referral_invite import (
    attach_school_signup_to_referral,
    create_referral_for_student,
    is_school_not_listed,
    resolve_referral_token,
)
from app.models.school import SchoolProfile
from app.services.school_constants import SCHOOL_AFFILIATIONS, VALID_AFFILIATION_IDS
from app.services.legal_terms import enforce_signup_legal_bundle
from app.services.signup_validation import (
    assert_email_available_for_new_signup,
    assert_signup_resubmit_allowed,
    availability_flags_for_signup,
    find_signup_by_persona_email,
    validate_email_format,
)


router = APIRouter(prefix="/signup", tags=["signup"])
logger = logging.getLogger(__name__)


@router.get("/check-availability")
async def check_signup_availability(
    email: Optional[str] = None,
    pan: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Pre-submit check — if email or PAN is already registered, the client should
    prompt the user to sign in instead of creating a duplicate account.
    """
    out: dict = {
        "email_available": True,
        "pan_available": True,
        "email_registered": False,
        "pan_registered": False,
        "email_resubmit_allowed": False,
        "pan_resubmit_allowed": False,
        "message": None,
    }

    if email and email.strip():
        try:
            norm_email = validate_email_format(email)
        except HTTPException as exc:
            out["email_available"] = False
            out["message"] = str(exc.detail)
            return out
        res = await db.execute(
            select(SignupRequest).where(func.lower(SignupRequest.email) == norm_email)
        )
        rows = res.scalars().all()
        if rows:
            # Same email should not exist on multiple rows; use first for gate flags.
            flags = availability_flags_for_signup(rows[0])
            out["email_available"] = flags["available"]
            out["email_registered"] = flags["registered"]
            out["email_resubmit_allowed"] = flags["resubmit_allowed"]
            if flags["message"]:
                out["message"] = flags["message"]

    if pan and pan.strip():
        norm_pan = pan.strip().upper()
        res = await db.execute(
            select(SignupRequest).where(func.upper(SignupRequest.pan_number) == norm_pan)
        )
        signup = res.scalars().first()
        if signup:
            flags = availability_flags_for_signup(signup)
            out["pan_available"] = flags["available"]
            out["pan_registered"] = flags["registered"]
            out["pan_resubmit_allowed"] = flags["resubmit_allowed"]
            if flags["message"] and not out["message"]:
                out["message"] = flags["message"].replace("email", "PAN")

    return out


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HTTPException(status_code=400, detail=message)



def _validate_pan_field(pan_number: str) -> str:
    pan = (pan_number or "").strip().upper()
    _require(bool(pan), "PAN number is required")
    _require(
        bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan)),
        "Invalid PAN format (example: ABCDE1234F)",
    )
    return pan


async def _process_signup_common(
    *,
    persona: Persona,
    signup: Optional[SignupRequest],
    full_name: str,
    mobile: str,
    email: str,
    password: str,
    address_line1: str,
    address_line2: str,
    city: str,
    state: str,
    pincode: str,
    country: str,
    kyc_docs: list[UploadFile],
    db: AsyncSession,
) -> SignupRequest:
    """Common logic for creating/updating signup and saving KYC docs."""
    (
        mobile,
        country,
        pincode,
        state,
        city,
        address_line1,
        address_line2,
    ) = validate_signup_contact_address(
        mobile=mobile,
        country=country,
        pincode=pincode,
        state=state,
        city=city,
        address_line1=address_line1,
        address_line2=address_line2,
    )

    norm_email = validate_email_format(email)
    if signup:
        assert_signup_resubmit_allowed(signup)
    else:
        await assert_email_available_for_new_signup(db, norm_email)

    _require(len(kyc_docs) > 0, "At least one KYC document is required")

    now = datetime.utcnow()
    password_hash = hash_password(password)

    if not signup:
        signup = SignupRequest(
            persona=persona,
            full_name=full_name,
            mobile=mobile,
            email=norm_email,
            password_hash=password_hash,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            pincode=pincode,
            country=country,
            created_at=now,
            updated_at=now,
        )
        db.add(signup)
        await db.flush()
    else:
        signup.full_name = full_name
        signup.mobile = mobile
        signup.password_hash = password_hash  # Update password on re-submission
        signup.address_line1 = address_line1
        signup.address_line2 = address_line2
        signup.city = city
        signup.state = state
        signup.pincode = pincode
        signup.country = country
        signup.kyc_status = KycStatus.pending
        signup.admin_note = None
        signup.updated_at = now

    # Overwrite docs by original filename
    existing_docs_res = await db.execute(select(KycDocument).where(KycDocument.signup_id == signup.id))
    existing_docs = {d.original_filename: d for d in existing_docs_res.scalars().all()}

    for f in kyc_docs:
        original_filename = f.filename or "kyc_document"
        stored_filename, stored_path, content_type = await save_kyc_file(signup_id=signup.id, file=f)

        old = existing_docs.get(original_filename)
        if old:
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

    await db.commit()
    await db.refresh(signup)
    return signup


async def _send_admin_notification(persona: Persona, signup: SignupRequest, db: AsyncSession) -> None:
    """Send admin notification email for new registrations."""
    if signup.kyc_status != KycStatus.pending:
        return

    persona_labels = {
        Persona.sponsor: "Sponsor",
        Persona.sponsor_leader: "Sponsor Leader",
        Persona.sponsor_member: "Circle Member",
        Persona.vendor: "Vendor",
        Persona.student: "Student",
        Persona.school: "School Partner",
    }
    label = persona_labels.get(persona, "User")
    school_line = ""
    if persona == Persona.school and signup.school_name:
        school_line = f"- School: {signup.school_name}\n- Affiliation: {signup.school_affiliation or '—'}\n"

    mobile_display = format_mobile_display(signup.mobile, signup.country)
    subject = f"New {label} Registration Pending KYC Approval"
    text_body = (
        f"Hello Admin,\n\n"
        f"A new {label} has registered on Zenk and is awaiting KYC review.\n\n"
        f"- Signup ID: {signup.id}\n"
        f"- Name: {signup.full_name}\n"
        f"- Email: {signup.email}\n"
        f"- Mobile: {mobile_display}\n"
        f"{school_line}"
        f"- Current Status: {signup.kyc_status.value}\n\n"
        f"Please login to Zenk ({settings.website_url}) to review the KYC documents and approve.\n\n"
        "Regards,\n"
        "Zenk Admin\n"
    )
    html_body = render_admin_notification_html(
        persona_label=label,
        signup_id=signup.id,
        full_name=signup.full_name,
        email=signup.email,
        mobile=mobile_display,
        kyc_status=signup.kyc_status.value,
        website_url=settings.website_url,
    )
    try:
        await send_email(
            subject=subject,
            to_email=settings.admin_notification_to,
            text_body=text_body,
            html_body=html_body,
        )
    except Exception:
        logger.exception("Failed to send admin notification email for signup_id=%s", signup.id)
    
    # Create in-app notification for admin
    try:
        await notify_admin_new_signup(
            signup_id=signup.id,
            persona=label,
            full_name=signup.full_name,
            email=signup.email,
            db=db,
        )
    except Exception:
        logger.exception("Failed to create admin notification for signup_id=%s", signup.id)


@router.post(
    "/sponsor",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_sponsor(
    request: Request,
    # Common fields
    full_name: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    address_line1: str = Form(...),
    address_line2: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    country: str = Form(...),
    # Sponsor-specific fields
    sponsor_type: str = Form(...),
    pan_number: Optional[str] = Form(default=None),
    company_name: Optional[str] = Form(default=None),
    company_registration_number: Optional[str] = Form(default=None),
    gst_number: Optional[str] = Form(default=None),
    authorized_signatory_name: Optional[str] = Form(default=None),
    authorized_signatory_designation: Optional[str] = Form(default=None),
    # KYC docs - accept single file (kyc_doc) or multiple files (kyc_docs)
    kyc_doc: Optional[UploadFile] = File(default=None),
    kyc_docs: Optional[list[UploadFile]] = File(default=None),
    terms_version: str = Form(...),
    terms_accepted: str = Form(...),
    privacy_version: str = Form(...),
    privacy_accepted: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Sponsor signup endpoint (form-data with file uploads)."""
    # Validate password
    _require(password == confirm_password, "Password and confirm password do not match")
    _require(len(password) >= 8, "Password must be at least 8 characters long")
    _require(sponsor_type in {"individual", "company"}, "sponsor_type must be 'individual' or 'company'")
    
    if sponsor_type == "individual":
        _require(bool(pan_number), "pan_number is required for sponsor individual")
    else:
        _require(bool(company_name), "company_name is required for sponsor company")
        _require(bool(company_registration_number), "company_registration_number is required for sponsor company")
        _require(bool(gst_number), "gst_number is required for sponsor company")
        _require(bool(authorized_signatory_name), "authorized_signatory_name is required for sponsor company")
        _require(bool(authorized_signatory_designation), "authorized_signatory_designation is required for sponsor company")

    # Combine single file and multiple files into one list
    all_files: list[UploadFile] = []
    if kyc_doc:
        all_files.append(kyc_doc)
    if kyc_docs:
        all_files.extend(kyc_docs)
    
    _require(len(all_files) > 0, "At least one KYC document is required (use kyc_doc or kyc_docs)")

    email = validate_email_format(email)
    signup = await find_signup_by_persona_email(db, persona=Persona.sponsor, email=email)

    signup = await _process_signup_common(
        persona=Persona.sponsor,
        signup=signup,
        full_name=full_name,
        mobile=mobile,
        email=email,
        password=password,
        address_line1=address_line1,
        address_line2=address_line2,
        city=city,
        state=state,
        pincode=pincode,
        country=country,
        kyc_docs=all_files,
        db=db,
    )

    # Update sponsor-specific fields
    signup.sponsor_type = sponsor_type
    signup.pan_number = pan_number
    signup.company_name = company_name
    signup.company_registration_number = company_registration_number
    signup.gst_number = gst_number
    signup.authorized_signatory_name = authorized_signatory_name
    signup.authorized_signatory_designation = authorized_signatory_designation
    await enforce_signup_legal_bundle(
        db,
        request,
        signup,
        terms_version=terms_version,
        terms_accepted=terms_accepted,
        privacy_version=privacy_version,
        privacy_accepted=privacy_accepted,
    )
    await db.commit()
    await db.refresh(signup)

    await _send_admin_notification(Persona.sponsor, signup, db)

    docs_res = await db.execute(select(KycDocument).where(KycDocument.signup_id == signup.id))
    docs = docs_res.scalars().all()

    return SignupResponse(
        id=signup.id,
        persona=signup.persona,
        full_name=signup.full_name,
        mobile=signup.mobile,
        email=signup.email,
        kyc_status=signup.kyc_status,
        documents=[
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "stored_filename": d.stored_filename,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    )


@router.post(
    "/sponsor_leader",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_sponsor_leader(
    request: Request,
    full_name: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    address_line1: str = Form(...),
    address_line2: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    country: str = Form(...),
    sponsor_type: str = Form(...),
    pan_number: Optional[str] = Form(default=None),
    company_name: Optional[str] = Form(default=None),
    company_registration_number: Optional[str] = Form(default=None),
    gst_number: Optional[str] = Form(default=None),
    authorized_signatory_name: Optional[str] = Form(default=None),
    authorized_signatory_designation: Optional[str] = Form(default=None),
    kyc_doc: Optional[UploadFile] = File(default=None),
    kyc_docs: Optional[list[UploadFile]] = File(default=None),
    terms_version: str = Form(...),
    terms_accepted: str = Form(...),
    privacy_version: str = Form(...),
    privacy_accepted: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Sponsor circle leader signup — full KYC before circle setup."""
    _require(password == confirm_password, "Password and confirm password do not match")
    _require(len(password) >= 8, "Password must be at least 8 characters long")
    _require(sponsor_type in {"individual", "company"}, "sponsor_type must be 'individual' or 'company'")

    if sponsor_type == "individual":
        _require(bool(pan_number), "pan_number is required for sponsor individual")
    else:
        _require(bool(company_name), "company_name is required for sponsor company")
        _require(bool(company_registration_number), "company_registration_number is required for sponsor company")
        _require(bool(gst_number), "gst_number is required for sponsor company")
        _require(bool(authorized_signatory_name), "authorized_signatory_name is required for sponsor company")
        _require(bool(authorized_signatory_designation), "authorized_signatory_designation is required for sponsor company")

    all_files: list[UploadFile] = []
    if kyc_doc:
        all_files.append(kyc_doc)
    if kyc_docs:
        all_files.extend(kyc_docs)
    _require(len(all_files) > 0, "At least one KYC document is required (use kyc_doc or kyc_docs)")

    email = validate_email_format(email)
    signup = await find_signup_by_persona_email(db, persona=Persona.sponsor_leader, email=email)

    signup = await _process_signup_common(
        persona=Persona.sponsor_leader,
        signup=signup,
        full_name=full_name,
        mobile=mobile,
        email=email,
        password=password,
        address_line1=address_line1,
        address_line2=address_line2,
        city=city,
        state=state,
        pincode=pincode,
        country=country,
        kyc_docs=all_files,
        db=db,
    )

    signup.sponsor_type = sponsor_type
    signup.pan_number = pan_number
    signup.company_name = company_name
    signup.company_registration_number = company_registration_number
    signup.gst_number = gst_number
    signup.authorized_signatory_name = authorized_signatory_name
    signup.authorized_signatory_designation = authorized_signatory_designation
    await enforce_signup_legal_bundle(
        db,
        request,
        signup,
        terms_version=terms_version,
        terms_accepted=terms_accepted,
        privacy_version=privacy_version,
        privacy_accepted=privacy_accepted,
    )
    await db.commit()
    await db.refresh(signup)

    await _send_admin_notification(Persona.sponsor_leader, signup, db)

    docs_res = await db.execute(select(KycDocument).where(KycDocument.signup_id == signup.id))
    docs = docs_res.scalars().all()

    return SignupResponse(
        id=signup.id,
        persona=signup.persona,
        full_name=signup.full_name,
        mobile=signup.mobile,
        email=signup.email,
        kyc_status=signup.kyc_status,
        documents=[
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "stored_filename": d.stored_filename,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    )


@router.post(
    "/sponsor_member",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_sponsor_member(
    request: Request,
    full_name: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    address_line1: str = Form(...),
    address_line2: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    country: str = Form(...),
    pan_number: Optional[str] = Form(default=None),
    circle_invite_code: Optional[str] = Form(default=None),
    is_parent_guardian: bool = Form(default=False),
    linked_student_signup_id: Optional[str] = Form(default=None),
    kyc_doc: Optional[UploadFile] = File(default=None),
    kyc_docs: Optional[list[UploadFile]] = File(default=None),
    terms_version: str = Form(...),
    terms_accepted: str = Form(...),
    privacy_version: str = Form(...),
    privacy_accepted: str = Form(...),
    parent_member_version: Optional[str] = Form(default=None),
    parent_member_accepted: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Circle member signup — joins a sponsor circle after leader invite."""
    _require(password == confirm_password, "Password and confirm password do not match")
    _require(len(password) >= 8, "Password must be at least 8 characters long")
    pan_number = _validate_pan_field(pan_number or "")

    all_files: list[UploadFile] = []
    if kyc_doc:
        all_files.append(kyc_doc)
    if kyc_docs:
        all_files.extend(kyc_docs)
    _require(len(all_files) > 0, "At least one ID document is required (use kyc_doc or kyc_docs)")

    email = validate_email_format(email)
    signup = await find_signup_by_persona_email(db, persona=Persona.sponsor_member, email=email)

    signup = await _process_signup_common(
        persona=Persona.sponsor_member,
        signup=signup,
        full_name=full_name,
        mobile=mobile,
        email=email,
        password=password,
        address_line1=address_line1,
        address_line2=address_line2,
        city=city,
        state=state,
        pincode=pincode,
        country=country,
        kyc_docs=all_files,
        db=db,
    )

    from app.models.enums import MemberKind
    from app.services.student_family import build_parent_admin_note, upsert_family_link

    signup.pan_number = pan_number
    if is_parent_guardian:
        signup.member_kind = MemberKind.parent_guardian.value
        signup.linked_student_signup_id = linked_student_signup_id
    invite_circle_id = ""
    if circle_invite_code and circle_invite_code.strip():
        from app.services.circle_member_invite import build_invite_note
        from app.services.circle_invite_token import is_uuid_like, resolve_invite_token

        raw_invite = circle_invite_code.strip()
        if is_uuid_like(raw_invite):
            invite_circle_id = raw_invite
        else:
            resolved = await resolve_invite_token(db, raw_invite)
            if not resolved:
                raise HTTPException(
                    status_code=400,
                    detail="Circle invite link is invalid or expired. Ask your leader for a new link.",
                )
            invite_circle_id, _ = resolved
        if is_parent_guardian and linked_student_signup_id:
            signup.admin_note = build_parent_admin_note(
                circle_id=invite_circle_id,
                student_signup_id=linked_student_signup_id,
            )
        else:
            signup.admin_note = build_invite_note(invite_circle_id)
    elif is_parent_guardian and linked_student_signup_id:
        signup.admin_note = build_parent_admin_note(
            circle_id="",
            student_signup_id=linked_student_signup_id,
        )
    member_role = "parent_guardian" if is_parent_guardian else "self"
    await enforce_signup_legal_bundle(
        db,
        request,
        signup,
        terms_version=terms_version,
        terms_accepted=terms_accepted,
        privacy_version=privacy_version,
        privacy_accepted=privacy_accepted,
        parent_member_version=parent_member_version if is_parent_guardian else None,
        parent_member_accepted=parent_member_accepted if is_parent_guardian else None,
        acceptance_role=member_role,
    )
    await db.commit()
    await db.refresh(signup)

    if is_parent_guardian and linked_student_signup_id:
        student_res = await db.execute(
            select(SignupRequest).where(
                SignupRequest.id == linked_student_signup_id,
                SignupRequest.persona == Persona.student,
            )
        )
        student_row = student_res.scalar_one_or_none()
        if student_row:
            await upsert_family_link(
                db,
                student_signup_id=student_row.id,
                parent_signup_id=signup.id,
                relationship=student_row.guardian_relationship or "parent",
                circle_id=invite_circle_id or None,
            )
            await db.commit()

    await _send_admin_notification(Persona.sponsor_member, signup, db)
    if invite_circle_id:
        try:
            label = f"{signup.full_name} (parent guardian)" if is_parent_guardian else signup.full_name
            await notify_circle_leaders_member_application(
                circle_id=invite_circle_id,
                member_signup_id=signup.id,
                member_name=label,
                member_email=signup.email,
                db=db,
            )
        except Exception:
            logger.exception(
                "Failed to notify circle leaders for member signup_id=%s circle_id=%s",
                signup.id,
                invite_circle_id,
            )

    docs_res = await db.execute(select(KycDocument).where(KycDocument.signup_id == signup.id))
    docs = docs_res.scalars().all()

    return SignupResponse(
        id=signup.id,
        persona=signup.persona,
        full_name=signup.full_name,
        mobile=signup.mobile,
        email=signup.email,
        kyc_status=signup.kyc_status,
        documents=[
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "stored_filename": d.stored_filename,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    )


@router.post(
    "/vendor",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_vendor(
    request: Request,
    # Common fields
    full_name: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    address_line1: str = Form(...),
    address_line2: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    country: str = Form(...),
    # Vendor-specific fields
    business_name: str = Form(...),
    business_type: str = Form(...),
    gst_number: str = Form(...),
    pan_number: str = Form(...),
    product_categories: str = Form(...),
    website: str = Form(...),
    # KYC docs - accept single file (kyc_doc) or multiple files (kyc_docs)
    kyc_doc: Optional[UploadFile] = File(default=None),
    kyc_docs: Optional[list[UploadFile]] = File(default=None),
    terms_version: str = Form(...),
    terms_accepted: str = Form(...),
    privacy_version: str = Form(...),
    privacy_accepted: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Vendor/Service Provider signup endpoint (form-data with file uploads)."""
    # Validate password
    _require(password == confirm_password, "Password and confirm password do not match")
    _require(len(password) >= 8, "Password must be at least 8 characters long")
    
    # Combine single file and multiple files into one list
    all_files: list[UploadFile] = []
    if kyc_doc:
        all_files.append(kyc_doc)
    if kyc_docs:
        all_files.extend(kyc_docs)
    
    _require(len(all_files) > 0, "At least one KYC document is required (use kyc_doc or kyc_docs)")
    
    email = validate_email_format(email)
    signup = await find_signup_by_persona_email(db, persona=Persona.vendor, email=email)

    signup = await _process_signup_common(
        persona=Persona.vendor,
        signup=signup,
        full_name=full_name,
        mobile=mobile,
        email=email,
        password=password,
        address_line1=address_line1,
        address_line2=address_line2,
        city=city,
        state=state,
        pincode=pincode,
        country=country,
        kyc_docs=all_files,
        db=db,
    )

    # Update vendor-specific fields
    signup.business_name = business_name
    signup.business_type = business_type
    signup.gst_number = gst_number
    signup.pan_number = pan_number
    signup.product_categories = product_categories
    signup.website = website
    await enforce_signup_legal_bundle(
        db,
        request,
        signup,
        terms_version=terms_version,
        terms_accepted=terms_accepted,
        privacy_version=privacy_version,
        privacy_accepted=privacy_accepted,
    )
    await db.commit()
    await db.refresh(signup)

    await _send_admin_notification(Persona.vendor, signup, db)

    docs_res = await db.execute(select(KycDocument).where(KycDocument.signup_id == signup.id))
    docs = docs_res.scalars().all()

    return SignupResponse(
        id=signup.id,
        persona=signup.persona,
        full_name=signup.full_name,
        mobile=signup.mobile,
        email=signup.email,
        kyc_status=signup.kyc_status,
        documents=[
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "stored_filename": d.stored_filename,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    )


@router.get("/school/affiliations")
async def list_school_affiliations():
    """Affiliation board options for public school partner signup."""
    return SCHOOL_AFFILIATIONS


@router.get("/schools")
async def list_signup_schools(db: AsyncSession = Depends(get_db)):
    """Registered partner schools for student signup dropdown."""
    return await list_public_schools(db)


@router.get("/school-referral/resolve")
async def resolve_school_referral(token: str, db: AsyncSession = Depends(get_db)):
    """Public preview for a student-generated school invite link."""
    return await resolve_referral_token(db, token)


@router.post(
    "/school",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_school(
    request: Request,
    full_name: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    address_line1: str = Form(...),
    address_line2: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    country: str = Form(...),
    school_name: str = Form(...),
    school_principal_name: str = Form(...),
    school_affiliation: str = Form(...),
    school_affiliation_number: Optional[str] = Form(default=None),
    school_enrollment_year: Optional[str] = Form(default=None),
    kyc_doc: Optional[UploadFile] = File(default=None),
    kyc_docs: Optional[list[UploadFile]] = File(default=None),
    terms_version: str = Form(...),
    terms_accepted: str = Form(...),
    privacy_version: str = Form(...),
    privacy_accepted: str = Form(...),
    school_referral_token: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Public school partner signup — principal account; ZenK admin reviews KYC."""
    _require(password == confirm_password, "Password and confirm password do not match")
    _require(len(password) >= 8, "Password must be at least 8 characters long")

    affiliation_key = (school_affiliation or "").strip().upper()
    _require(affiliation_key in VALID_AFFILIATION_IDS, "Please select a valid school affiliation.")

    all_files: list[UploadFile] = []
    if kyc_doc:
        all_files.append(kyc_doc)
    if kyc_docs:
        all_files.extend(kyc_docs)
    _require(len(all_files) > 0, "At least one KYC document is required (affiliation or registration proof).")

    if school_enrollment_year and school_enrollment_year.strip():
        year = school_enrollment_year.strip()
        _require(year.isdigit() and 1950 <= int(year) <= 2100, "Enrollment year must be a valid year.")

    email = validate_email_format(email)
    signup = await find_signup_by_persona_email(db, persona=Persona.school, email=email)

    signup = await _process_signup_common(
        persona=Persona.school,
        signup=signup,
        full_name=full_name,
        mobile=mobile,
        email=email,
        password=password,
        address_line1=address_line1,
        address_line2=address_line2,
        city=city,
        state=state,
        pincode=pincode,
        country=country,
        kyc_docs=all_files,
        db=db,
    )

    signup.school_name = school_name.strip()[:300]
    signup.school_principal_name = (school_principal_name or full_name).strip()[:200]
    signup.school_affiliation = affiliation_key
    signup.school_affiliation_number = (school_affiliation_number or "").strip()[:64] or None
    signup.school_enrollment_year = (school_enrollment_year or "").strip()[:10] or None
    await enforce_signup_legal_bundle(
        db,
        request,
        signup,
        terms_version=terms_version,
        terms_accepted=terms_accepted,
        privacy_version=privacy_version,
        privacy_accepted=privacy_accepted,
    )
    await db.commit()
    await db.refresh(signup)

    if school_referral_token and school_referral_token.strip():
        await attach_school_signup_to_referral(
            db,
            token=school_referral_token.strip(),
            school_signup_id=signup.id,
        )
        await db.commit()

    await _send_admin_notification(Persona.school, signup, db)

    docs_res = await db.execute(select(KycDocument).where(KycDocument.signup_id == signup.id))
    docs = docs_res.scalars().all()

    return SignupResponse(
        id=signup.id,
        persona=signup.persona,
        full_name=signup.full_name,
        mobile=signup.mobile,
        email=signup.email,
        kyc_status=signup.kyc_status,
        documents=[
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "stored_filename": d.stored_filename,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    )


@router.post(
    "/student",
    response_model=StudentFamilySignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_student(
    request: Request,
    # Common fields
    full_name: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    address_line1: str = Form(...),
    address_line2: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    country: str = Form(...),
    # Student-specific fields
    date_of_birth: date = Form(...),
    school_id: str = Form(...),
    school_or_college_name: Optional[str] = Form(default=None),
    proposed_school_city: Optional[str] = Form(default=None),
    proposed_school_state: Optional[str] = Form(default=None),
    proposed_school_contact_email: Optional[str] = Form(default=None),
    grade_or_year: str = Form(...),
    guardian_name: str = Form(...),
    guardian_mobile: str = Form(...),
    guardian_relationship: str = Form(default="parent"),
    circle_invite_code: Optional[str] = Form(default=None),
    parent_pan_number: Optional[str] = Form(default=None),
    # KYC docs - accept single file (kyc_doc) or multiple files (kyc_docs)
    kyc_doc: Optional[UploadFile] = File(default=None),
    kyc_docs: Optional[list[UploadFile]] = File(default=None),
    parent_kyc_doc: Optional[UploadFile] = File(default=None),
    parent_kyc_docs: Optional[list[UploadFile]] = File(default=None),
    terms_version: str = Form(...),
    terms_accepted: str = Form(...),
    privacy_version: str = Form(...),
    privacy_accepted: str = Form(...),
    parent_member_version: Optional[str] = Form(default=None),
    parent_member_accepted: Optional[str] = Form(default=None),
    student_declaration_version: Optional[str] = Form(default=None),
    student_declaration_accepted: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Student signup — also creates linked parent/guardian member account (same email + password)."""
    _require(password == confirm_password, "Password and confirm password do not match")
    _require(len(password) >= 8, "Password must be at least 8 characters long")
    _require(guardian_relationship.strip(), "Guardian relationship is required")
    parent_pan_number = _validate_pan_field(parent_pan_number or "")

    all_files: list[UploadFile] = []
    if kyc_doc:
        all_files.append(kyc_doc)
    if kyc_docs:
        all_files.extend(kyc_docs)
    _require(len(all_files) > 0, "At least one student KYC document is required (use kyc_doc or kyc_docs)")

    parent_files: list[UploadFile] = []
    if parent_kyc_doc:
        parent_files.append(parent_kyc_doc)
    if parent_kyc_docs:
        parent_files.extend(parent_kyc_docs)
    _require(len(parent_files) > 0, "Parent/guardian KYC documents are required (use parent_kyc_doc or parent_kyc_docs)")

    email = validate_email_format(email)
    signup = await find_signup_by_persona_email(db, persona=Persona.student, email=email)

    signup = await _process_signup_common(
        persona=Persona.student,
        signup=signup,
        full_name=full_name,
        mobile=mobile,
        email=email,
        password=password,
        address_line1=address_line1,
        address_line2=address_line2,
        city=city,
        state=state,
        pincode=pincode,
        country=country,
        kyc_docs=all_files,
        db=db,
    )
    guardian_mobile = validate_and_normalize_mobile(guardian_mobile, signup.country)

    school_res = await db.execute(select(SchoolProfile).where(SchoolProfile.id == school_id.strip()))
    school_profile = school_res.scalar_one_or_none()
    school_referral_url: Optional[str] = None

    if is_school_not_listed(school_id):
        proposed_name = (school_or_college_name or "").strip()
        proposed_city = (proposed_school_city or "").strip()
        _require(proposed_name, "Enter your school name")
        _require(proposed_city, "Enter your school city")
        access_tier = compute_login_access_tier(date_of_birth)
        signup.date_of_birth = date_of_birth
        signup.selected_school_id = None
        signup.school_or_college_name = proposed_name[:300]
        signup.onboarding_version = ONBOARDING_V2
        signup.grade_or_year = grade_or_year
        signup.guardian_name = guardian_name
        signup.guardian_mobile = guardian_mobile
        signup.guardian_relationship = guardian_relationship.strip()
        signup.login_access_tier = access_tier.value
        await db.commit()
        await db.refresh(signup)
    else:
        if not school_profile:
            raise HTTPException(status_code=400, detail="Please select a registered school from the list")

        access_tier = compute_login_access_tier(date_of_birth)
        signup.date_of_birth = date_of_birth
        signup.selected_school_id = school_profile.id
        signup.school_or_college_name = school_or_college_name or school_profile.school_name
        signup.onboarding_version = ONBOARDING_V2
        signup.grade_or_year = grade_or_year
        signup.guardian_name = guardian_name
        signup.guardian_mobile = guardian_mobile
        signup.guardian_relationship = guardian_relationship.strip()
        signup.login_access_tier = access_tier.value
        await db.commit()
        await db.refresh(signup)

    invite_circle_id = ""
    if circle_invite_code and circle_invite_code.strip():
        from app.services.circle_invite_token import is_uuid_like, resolve_invite_token

        raw_invite = circle_invite_code.strip()
        if is_uuid_like(raw_invite):
            invite_circle_id = raw_invite
        else:
            resolved = await resolve_invite_token(db, raw_invite)
            if not resolved:
                raise HTTPException(
                    status_code=400,
                    detail="Circle invite link is invalid or expired. Ask your leader for a new link.",
                )
            invite_circle_id, _ = resolved

    parent_signup = await create_parent_guardian_signup(
        db,
        student_signup=signup,
        guardian_name=guardian_name,
        guardian_mobile=guardian_mobile,
        password=password,
        circle_id=invite_circle_id,
        parent_pan_number=parent_pan_number,
        parent_kyc_docs=parent_files or None,
    )
    family_link = await upsert_family_link(
        db,
        student_signup_id=signup.id,
        parent_signup_id=parent_signup.id,
        relationship=guardian_relationship.strip(),
        circle_id=invite_circle_id or None,
    )
    school_referral_url: Optional[str] = None
    if is_school_not_listed(school_id):
        _, school_referral_url = await create_referral_for_student(
            db,
            student_signup_id=signup.id,
            proposed_school_name=signup.school_or_college_name or "",
            proposed_city=proposed_school_city or "",
            proposed_state=proposed_school_state,
            proposed_contact_email=proposed_school_contact_email,
        )
    else:
        await create_school_interest(db, student_signup_id=signup.id, school_id=school_profile.id)
    await enforce_signup_legal_bundle(
        db,
        request,
        signup,
        terms_version=terms_version,
        terms_accepted=terms_accepted,
        privacy_version=privacy_version,
        privacy_accepted=privacy_accepted,
        student_declaration_version=student_declaration_version,
        student_declaration_accepted=student_declaration_accepted,
        acceptance_role="guardian_on_behalf",
    )
    await enforce_signup_legal_bundle(
        db,
        request,
        parent_signup,
        terms_version=terms_version,
        terms_accepted=terms_accepted,
        privacy_version=privacy_version,
        privacy_accepted=privacy_accepted,
        parent_member_version=parent_member_version,
        parent_member_accepted=parent_member_accepted,
        acceptance_role="parent_guardian",
    )
    await db.commit()
    await db.refresh(parent_signup)
    await db.refresh(family_link)

    await _send_admin_notification(Persona.student, signup, db)
    await _send_admin_notification(Persona.sponsor_member, parent_signup, db)

    # Parent joins circle only after student is school-enrolled and circle-approved (see family_circle_provision).

    docs_res = await db.execute(select(KycDocument).where(KycDocument.signup_id == signup.id))
    docs = docs_res.scalars().all()

    return StudentFamilySignupResponse(
        id=signup.id,
        persona=signup.persona,
        full_name=signup.full_name,
        mobile=signup.mobile,
        email=signup.email,
        kyc_status=signup.kyc_status,
        parent_signup_id=parent_signup.id,
        login_access_tier=access_tier.value,
        family_link_id=family_link.id,
        school_referral_url=school_referral_url,
        documents=[
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "stored_filename": d.stored_filename,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    )


@router.get("/{signup_id}", response_model=SignupResponse)
async def get_signup(signup_id: str, db: AsyncSession = Depends(get_db)):
    """Get signup status by ID."""
    res = await db.execute(
        select(SignupRequest)
        .options(selectinload(SignupRequest.documents))
        .where(SignupRequest.id == signup_id)
    )
    signup = res.scalar_one_or_none()
    if not signup:
        raise HTTPException(status_code=404, detail="Signup not found")

    return SignupResponse(
        id=signup.id,
        persona=signup.persona,
        full_name=signup.full_name,
        mobile=signup.mobile,
        email=signup.email,
        kyc_status=signup.kyc_status,
        documents=[
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "stored_filename": d.stored_filename,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in signup.documents
        ],
    )


@router.get("/{signup_id}/details", response_model=FullSignupDetails)
async def get_signup_details(signup_id: str, db: AsyncSession = Depends(get_db)):
    """Get complete signup details for admin review (excluding password)."""
    res = await db.execute(
        select(SignupRequest)
        .options(selectinload(SignupRequest.documents))
        .where(SignupRequest.id == signup_id)
    )
    signup = res.scalar_one_or_none()
    if not signup:
        raise HTTPException(status_code=404, detail="Signup not found")

    return FullSignupDetails(
        id=signup.id,
        persona=signup.persona,
        kyc_status=signup.kyc_status,
        admin_note=signup.admin_note,
        created_at=signup.created_at.isoformat() if signup.created_at else None,
        updated_at=signup.updated_at.isoformat() if signup.updated_at else None,
        # Common fields
        full_name=signup.full_name,
        mobile=signup.mobile,
        email=signup.email,
        address_line1=signup.address_line1,
        address_line2=signup.address_line2,
        city=signup.city,
        state=signup.state,
        pincode=signup.pincode,
        country=signup.country,
        # Sponsor fields
        sponsor_type=signup.sponsor_type,
        pan_number=signup.pan_number,
        company_name=signup.company_name,
        company_registration_number=signup.company_registration_number,
        gst_number=signup.gst_number,
        authorized_signatory_name=signup.authorized_signatory_name,
        authorized_signatory_designation=signup.authorized_signatory_designation,
        # Vendor fields
        business_name=signup.business_name,
        business_type=signup.business_type,
        product_categories=signup.product_categories,
        website=signup.website,
        # Student fields
        date_of_birth=signup.date_of_birth.isoformat() if signup.date_of_birth else None,
        school_or_college_name=signup.school_or_college_name,
        grade_or_year=signup.grade_or_year,
        guardian_name=signup.guardian_name,
        guardian_mobile=signup.guardian_mobile,
        guardian_relationship=signup.guardian_relationship,
        login_access_tier=signup.login_access_tier,
        member_kind=signup.member_kind,
        linked_student_signup_id=signup.linked_student_signup_id,
        documents=[
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "stored_filename": d.stored_filename,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in signup.documents
        ],
    )
