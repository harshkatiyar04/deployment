from datetime import date, datetime
from pathlib import Path
from typing import Optional
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.enums import KycStatus, Persona
from app.models.signup import KycDocument, SignupRequest
from app.schemas.signup import SignupResponse, FullSignupDetails
from app.core.settings import settings
from app.core.security import hash_password
from app.services.email import send_email
from app.services.email_templates import render_admin_notification_html
from app.services.notifications import notify_admin_new_signup
from app.services.storage import save_kyc_file


router = APIRouter(prefix="/signup", tags=["signup"])
logger = logging.getLogger(__name__)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HTTPException(status_code=400, detail=message)


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
    """Common logic for creating/updating signup and saving KYC docs.
    
    Accepts kyc_docs as a list of files (can be empty list if kyc_doc is provided).
    """
    """Common logic for creating/updating signup and saving KYC docs."""
    if signup and signup.kyc_status == KycStatus.approved:
        raise HTTPException(status_code=409, detail="Signup already approved; changes are not allowed")

    _require(len(kyc_docs) > 0, "At least one KYC document is required")

    now = datetime.utcnow()
    password_hash = hash_password(password)
    
    if not signup:
        signup = SignupRequest(
            persona=persona,
            full_name=full_name,
            mobile=mobile,
            email=email,
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
        Persona.vendor: "Vendor",
        Persona.student: "Student",
    }
    label = persona_labels.get(persona, "User")

    subject = f"New {label} Registration Pending KYC Approval"
    text_body = (
        f"Hello Admin,\n\n"
        f"A new {label} has registered on Zenk and is awaiting KYC review.\n\n"
        f"- Signup ID: {signup.id}\n"
        f"- Name: {signup.full_name}\n"
        f"- Email: {signup.email}\n"
        f"- Mobile: {signup.mobile}\n"
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
        mobile=signup.mobile,
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

    existing_res = await db.execute(
        select(SignupRequest).where(SignupRequest.persona == Persona.sponsor, SignupRequest.email == email)
    )
    signup = existing_res.scalar_one_or_none()

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
    "/vendor",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_vendor(
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
    
    existing_res = await db.execute(
        select(SignupRequest).where(SignupRequest.persona == Persona.vendor, SignupRequest.email == email)
    )
    signup = existing_res.scalar_one_or_none()

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


@router.post(
    "/student",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_student(
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
    school_or_college_name: str = Form(...),
    grade_or_year: str = Form(...),
    guardian_name: str = Form(...),
    guardian_mobile: str = Form(...),
    # KYC docs - accept single file (kyc_doc) or multiple files (kyc_docs)
    kyc_doc: Optional[UploadFile] = File(default=None),
    kyc_docs: Optional[list[UploadFile]] = File(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Student signup endpoint (form-data with file uploads)."""
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
    
    existing_res = await db.execute(
        select(SignupRequest).where(SignupRequest.persona == Persona.student, SignupRequest.email == email)
    )
    signup = existing_res.scalar_one_or_none()

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

    # Update student-specific fields
    signup.date_of_birth = date_of_birth
    signup.school_or_college_name = school_or_college_name
    signup.grade_or_year = grade_or_year
    signup.guardian_name = guardian_name
    signup.guardian_mobile = guardian_mobile
    await db.commit()
    await db.refresh(signup)

    await _send_admin_notification(Persona.student, signup, db)

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
        # Documents metadata
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
