"""Student–parent family accounts: linking, age gate, hat switching."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.enums import KycStatus, LoginAccessTier, MemberKind, Persona
from app.models.signup import KycDocument, SignupRequest
from app.models.student_family import StudentFamilyLink
from app.services.circle_member_invite import build_invite_note
from app.services.storage import save_kyc_file

# Under 15: guardian must mediate (IT Rules / DPDPA verifiable parental consent for minors).
_GUARDIAN_ONLY_MAX_AGE = 15
# 18+: Indian Majority Act — independent login without ongoing guardian gate.
_INDEPENDENT_MIN_AGE = 18


def compute_age_years(dob: date, *, on_day: Optional[date] = None) -> int:
    today = on_day or date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def compute_login_access_tier(dob: date) -> LoginAccessTier:
    age = compute_age_years(dob)
    if age >= _INDEPENDENT_MIN_AGE:
        return LoginAccessTier.independent
    if age >= _GUARDIAN_ONLY_MAX_AGE:
        return LoginAccessTier.consent_required
    return LoginAccessTier.guardian_only


def build_parent_admin_note(
    *,
    circle_id: str = "",
    student_signup_id: str,
    leader_status: str = "pending",
) -> str:
    parts: list[str] = []
    if circle_id:
        parts.append(build_invite_note(circle_id, leader_status=leader_status))
    parts.append(f"member_kind={MemberKind.parent_guardian.value}")
    parts.append(f"linked_student={student_signup_id}")
    parts.append("role_label=Parent guardian (circle member)")
    return "|".join(parts)


async def _copy_kyc_documents(
    db: AsyncSession,
    *,
    source_signup_id: str,
    target_signup_id: str,
) -> None:
    res = await db.execute(select(KycDocument).where(KycDocument.signup_id == source_signup_id))
    for doc in res.scalars().all():
        db.add(
            KycDocument(
                signup_id=target_signup_id,
                original_filename=doc.original_filename,
                stored_filename=doc.stored_filename,
                stored_path=doc.stored_path,
                content_type=doc.content_type,
            )
        )


async def _save_kyc_uploads(
    db: AsyncSession,
    *,
    signup_id: str,
    kyc_docs: list[UploadFile],
) -> None:
    existing_docs_res = await db.execute(select(KycDocument).where(KycDocument.signup_id == signup_id))
    existing_docs = {d.original_filename: d for d in existing_docs_res.scalars().all()}

    for f in kyc_docs:
        original_filename = f.filename or "kyc_document"
        stored_filename, stored_path, content_type = await save_kyc_file(signup_id=signup_id, file=f)
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
                    signup_id=signup_id,
                    original_filename=original_filename,
                    stored_filename=stored_filename,
                    stored_path=stored_path,
                    content_type=content_type,
                )
            )


async def create_parent_guardian_signup(
    db: AsyncSession,
    *,
    student_signup: SignupRequest,
    guardian_name: str,
    guardian_mobile: str,
    password: str,
    circle_id: str = "",
    parent_pan_number: Optional[str] = None,
    parent_kyc_docs: Optional[list[UploadFile]] = None,
    address_line1: Optional[str] = None,
    address_line2: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    pincode: Optional[str] = None,
    country: Optional[str] = None,
) -> SignupRequest:
    """Create sponsor_member row for parent/guardian — same email + password as student."""
    email = student_signup.email
    existing_res = await db.execute(
        select(SignupRequest).where(
            SignupRequest.persona == Persona.sponsor_member,
            func.lower(SignupRequest.email) == normalize_email(email),
        )
    )
    parent = existing_res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    password_hash = hash_password(password)

    if parent and parent.kyc_status == KycStatus.approved:
        raise HTTPException(status_code=409, detail="Parent member account already approved for this email")

    if not parent:
        parent = SignupRequest(
            persona=Persona.sponsor_member,
            full_name=guardian_name.strip(),
            mobile=guardian_mobile.strip(),
            email=email,
            password_hash=password_hash,
            address_line1=address_line1 or student_signup.address_line1,
            address_line2=address_line2 or student_signup.address_line2,
            city=city or student_signup.city,
            state=state or student_signup.state,
            pincode=pincode or student_signup.pincode,
            country=country or student_signup.country,
            member_kind=MemberKind.parent_guardian.value,
            linked_student_signup_id=student_signup.id,
            pan_number=parent_pan_number,
            admin_note=build_parent_admin_note(circle_id=circle_id, student_signup_id=student_signup.id),
            created_at=now,
            updated_at=now,
        )
        db.add(parent)
        await db.flush()
    else:
        parent.full_name = guardian_name.strip()
        parent.mobile = guardian_mobile.strip()
        parent.password_hash = password_hash
        parent.address_line1 = address_line1 or student_signup.address_line1
        parent.address_line2 = address_line2 or student_signup.address_line2
        parent.city = city or student_signup.city
        parent.state = state or student_signup.state
        parent.pincode = pincode or student_signup.pincode
        parent.country = country or student_signup.country
        parent.member_kind = MemberKind.parent_guardian.value
        parent.linked_student_signup_id = student_signup.id
        parent.pan_number = parent_pan_number or parent.pan_number
        parent.admin_note = build_parent_admin_note(circle_id=circle_id, student_signup_id=student_signup.id)
        parent.kyc_status = KycStatus.pending
        parent.updated_at = now

    if not parent_kyc_docs:
        raise HTTPException(status_code=400, detail="Parent/guardian KYC documents are required")
    await _save_kyc_uploads(db, signup_id=parent.id, kyc_docs=parent_kyc_docs)

    return parent


async def upsert_family_link(
    db: AsyncSession,
    *,
    student_signup_id: str,
    parent_signup_id: str,
    relationship: str,
    circle_id: Optional[str] = None,
) -> StudentFamilyLink:
    res = await db.execute(
        select(StudentFamilyLink).where(
            StudentFamilyLink.student_signup_id == student_signup_id,
            StudentFamilyLink.parent_signup_id == parent_signup_id,
        )
    )
    link = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if link:
        link.relationship = relationship
        link.circle_id = circle_id or link.circle_id
        link.updated_at = now
        return link

    link = StudentFamilyLink(
        student_signup_id=student_signup_id,
        parent_signup_id=parent_signup_id,
        relationship=relationship,
        circle_id=circle_id,
        created_at=now,
        updated_at=now,
    )
    db.add(link)
    await db.flush()
    return link


async def get_family_link_for_user(db: AsyncSession, signup_id: str) -> Optional[StudentFamilyLink]:
    res = await db.execute(
        select(StudentFamilyLink).where(
            (StudentFamilyLink.student_signup_id == signup_id)
            | (StudentFamilyLink.parent_signup_id == signup_id)
        )
    )
    return res.scalar_one_or_none()


async def resolve_linked_signup(
    db: AsyncSession,
    current: SignupRequest,
    target_hat: str,
) -> SignupRequest:
    """target_hat: 'student' | 'parent'."""
    link = await get_family_link_for_user(db, current.id)
    if not link:
        raise HTTPException(status_code=404, detail="No linked family account for this user")

    if target_hat == "student":
        if current.id == link.student_signup_id:
            return current
        res = await db.execute(select(SignupRequest).where(SignupRequest.id == link.student_signup_id))
        student = res.scalar_one_or_none()
        if not student:
            raise HTTPException(status_code=404, detail="Linked student account not found")
        return student

    if target_hat == "parent":
        if current.id == link.parent_signup_id:
            return current
        res = await db.execute(select(SignupRequest).where(SignupRequest.id == link.parent_signup_id))
        parent = res.scalar_one_or_none()
        if not parent or parent.member_kind != MemberKind.parent_guardian.value:
            raise HTTPException(status_code=404, detail="Linked parent account not found")
        return parent

    raise HTTPException(status_code=400, detail="target_hat must be 'student' or 'parent'")


def student_hat_available(student: SignupRequest, *, has_parental_consent: bool = False) -> bool:
    tier = student.login_access_tier or LoginAccessTier.consent_required.value
    if tier == LoginAccessTier.independent.value:
        return True
    if tier == LoginAccessTier.consent_required.value:
        return has_parental_consent
    return False


async def has_recorded_parental_consent(db: AsyncSession, student_signup_id: str) -> bool:
    from sqlalchemy import text

    res = await db.execute(
        text(
            'SELECT 1 FROM "ZENK".parental_consent_log WHERE student_id = :sid LIMIT 1'
        ),
        {"sid": student_signup_id},
    )
    return res.scalar_one_or_none() is not None


async def build_family_hats_context(db: AsyncSession, current: SignupRequest) -> dict:
    link = await get_family_link_for_user(db, current.id)
    if not link:
        return {
            "has_family": False,
            "active_hat": "student" if current.persona == Persona.student else "parent",
            "student": None,
            "parent": None,
            "circle_id": None,
        }

    student_res = await db.execute(select(SignupRequest).where(SignupRequest.id == link.student_signup_id))
    parent_res = await db.execute(select(SignupRequest).where(SignupRequest.id == link.parent_signup_id))
    student = student_res.scalar_one_or_none()
    parent = parent_res.scalar_one_or_none()

    consent = False
    if student:
        consent = await has_recorded_parental_consent(db, student.id)

    active_hat = "student" if current.persona == Persona.student else "parent"
    student_available = bool(student and student_hat_available(student, has_parental_consent=consent))

    return {
        "has_family": True,
        "active_hat": active_hat,
        "circle_id": link.circle_id,
        "relationship": link.relationship,
        "student": {
            "signup_id": student.id if student else None,
            "full_name": student.full_name if student else None,
            "kyc_status": student.kyc_status.value if student else None,
            "login_access_tier": student.login_access_tier if student else None,
            "can_switch": student_available,
            "requires_parent_unlock": (
                student.login_access_tier == LoginAccessTier.guardian_only.value if student else False
            ),
            "has_parental_consent": consent,
        }
        if student
        else None,
        "parent": {
            "signup_id": parent.id if parent else None,
            "full_name": parent.full_name if parent else None,
            "kyc_status": parent.kyc_status.value if parent else None,
            "member_kind": parent.member_kind if parent else None,
            "can_switch": parent is not None,
            "requires_password": True,
        }
        if parent
        else None,
    }


def verify_password_for_hat_switch(password: str, signup: SignupRequest) -> None:
    if not verify_password(password, signup.password_hash):
        raise HTTPException(status_code=401, detail="Password required to switch to parent view")
