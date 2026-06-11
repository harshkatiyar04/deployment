"""Authentication endpoints."""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.session import get_db
from app.models.enums import KycStatus, Persona
from app.models.signup import SignupRequest
from app.core.security import verify_password
from app.models.auth_log import AuthAuditLog
from app.services.signup_auth import resolve_signup_for_credentials
from app.core.jwt_auth import get_current_user
from app.services.circle_access import resolve_circle_access
from app.services.kyc_resubmit import list_signup_kyc_documents, resubmit_kyc_documents
from app.services.kyc_review import extract_kyc_review_note
from app.services.school_provision import ensure_school_profile
from app.services.student_family import (
    build_family_hats_context,
    resolve_linked_signup,
    student_hat_available,
    verify_password_for_hat_switch,
    has_recorded_parental_consent,
)
from app.models.enums import Persona

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


class LoginRequest(BaseModel):
    email: str
    password: str
    persona: Optional[Persona] = None  # Optional: if not provided, search across all personas


class CircleAccessOut(BaseModel):
    access_state: str
    redirect_to: str
    in_circle: bool = False
    circle_id: Optional[str] = None
    circle_name: Optional[str] = None
    leader_status: Optional[str] = None
    is_leader: bool = False


class CircleBanOut(BaseModel):
    banned: bool = True
    circle_id: str
    circle_name: Optional[str] = None
    reason: str
    banned_at: Optional[str] = None


class LoginResponse(BaseModel):
    id: str
    persona: Persona
    full_name: str
    email: str
    mobile: str
    kyc_status: KycStatus
    kyc_review_note: Optional[str] = None
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    circle_access: Optional[CircleAccessOut] = None
    circle_ban: Optional[CircleBanOut] = None


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")  # Brute-force protection
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login endpoint for authenticated users.
    
    Validates email and password, and checks if KYC is approved.
    If persona is not provided, searches across all personas for the email.
    """
    signup = await resolve_signup_for_credentials(
        db,
        email=body.email,
        password=body.password,
        persona=body.persona,
    )

    if not signup:
        logger.warning(f"Auth failure (/login): Account not found for email '{body.email}'")
        log = AuthAuditLog(
            email=body.email, 
            status="FAIL_EMAIL", 
            comment="Account not found",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(log)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Allow login regardless of KYC status (user can see home page)
    # Frontend can check kyc_status and show appropriate message
    status_message = "Welcome back — you're signed in."
    if signup.kyc_status == KycStatus.pending:
        status_message = (
            "Thank you for your patience. Your registration is with our team for verification. "
            "We'll email you at {email} as soon as your account is ready — usually within a few working days."
        ).format(email=signup.email)
    elif signup.kyc_status == KycStatus.rejected:
        status_message = (
            "We couldn't approve your registration with the documents provided. "
            "You can resubmit updated details and ID documents from your verification page — "
            "use the same email and password."
        )
    elif signup.kyc_status == KycStatus.info_required:
        status_message = (
            "We need a few more documents to complete your verification. "
            "Sign in to your verification page and upload what we've requested — "
            "you do not need to fill out the full application again."
        )
    
    log = AuthAuditLog(
        email=body.email, 
        status="SUCCESS", 
        comment=f"Persona: {signup.persona}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    from app.services.auth_tokens import issue_token_pair

    access_token, refresh_token = await issue_token_pair(db, signup.id)

    if signup.persona == Persona.school and signup.kyc_status == KycStatus.approved:
        await ensure_school_profile(db, signup, is_partner=True, onboarding_source="public_signup")

    await db.commit()

    access = await resolve_circle_access(db, signup)
    if signup.kyc_status == KycStatus.approved and signup.persona == Persona.sponsor_member:
        if access["access_state"] == "waiting_leader":
            status_message = (
                "Your identity verification is complete. "
                "Your circle leader still needs to approve your membership — "
                "we'll notify you when you can enter the circle."
            )

    from app.services.circle_ban_access import resolve_user_circle_ban

    ban_payload = await resolve_user_circle_ban(db, signup.id)
    circle_ban = CircleBanOut(**ban_payload) if ban_payload else None
    if circle_ban:
        status_message = (
            "Your account has been restricted following a safety report. "
            "Contact ZenK Admin below to request a review."
        )

    return LoginResponse(
        id=signup.id,
        persona=signup.persona,
        full_name=signup.full_name,
        email=signup.email,
        mobile=signup.mobile,
        kyc_status=signup.kyc_status,
        kyc_review_note=extract_kyc_review_note(signup.admin_note),
        message=status_message,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        circle_access=CircleAccessOut(**access),
        circle_ban=circle_ban,
    )


class SchoolOrgSummary(BaseModel):
    school_name: Optional[str] = None
    school_code: Optional[str] = None
    school_affiliation: Optional[str] = None
    profile_complete: Optional[bool] = None


class SessionUserResponse(BaseModel):
    id: str
    persona: Persona
    full_name: str
    email: str
    mobile: str
    kyc_status: KycStatus
    admin_note: Optional[str] = None
    kyc_review_note: Optional[str] = None
    circle_access: Optional[CircleAccessOut] = None
    circle_ban: Optional[CircleBanOut] = None
    school_org: Optional[SchoolOrgSummary] = None


class UserKycDocumentOut(BaseModel):
    id: str
    original_filename: str
    created_at: Optional[str] = None


async def _school_org_summary(db: AsyncSession, user: SignupRequest) -> Optional[SchoolOrgSummary]:
    if user.persona != Persona.school:
        return None
    from sqlalchemy import select
    from app.models.school import SchoolProfile
    from app.services.school_profile_completion import is_profile_complete

    res = await db.execute(select(SchoolProfile).where(SchoolProfile.id == user.id))
    profile = res.scalar_one_or_none()
    if profile:
        return SchoolOrgSummary(
            school_name=profile.school_name,
            school_code=profile.school_code,
            school_affiliation=profile.affiliation,
            profile_complete=is_profile_complete(profile),
        )
    return SchoolOrgSummary(
        school_name=user.school_name,
        school_code=None,
        school_affiliation=user.school_affiliation,
        profile_complete=False,
    )


@router.get("/me", response_model=SessionUserResponse, status_code=status.HTTP_200_OK)
async def get_session_user(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current user profile and KYC status (for verification tracking / refresh)."""
    from app.services.circle_ban_access import resolve_user_circle_ban

    access = await resolve_circle_access(db, user)
    ban_payload = await resolve_user_circle_ban(db, user.id)
    circle_ban = CircleBanOut(**ban_payload) if ban_payload else None
    return SessionUserResponse(
        id=user.id,
        persona=user.persona,
        full_name=user.full_name,
        email=user.email,
        mobile=user.mobile,
        kyc_status=user.kyc_status,
        admin_note=user.admin_note,
        kyc_review_note=extract_kyc_review_note(user.admin_note),
        circle_access=CircleAccessOut(**access),
        circle_ban=circle_ban,
        school_org=await _school_org_summary(db, user),
    )


@router.get("/me/kyc-documents", response_model=list[UserKycDocumentOut])
async def list_my_kyc_documents(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents already on file for the signed-in applicant."""
    docs = await list_signup_kyc_documents(db, user.id)
    return [
        UserKycDocumentOut(
            id=d.id,
            original_filename=d.original_filename,
            created_at=d.created_at.isoformat() if d.created_at else None,
        )
        for d in docs
    ]


@router.post("/me/kyc-documents/resubmit", response_model=SessionUserResponse)
async def resubmit_my_kyc_documents(
    kyc_docs: list[UploadFile] = File(...),
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload additional KYC documents when admin requested more information."""
    updated = await resubmit_kyc_documents(db, user, kyc_docs)
    access = await resolve_circle_access(db, updated)
    from app.services.circle_ban_access import resolve_user_circle_ban

    ban_payload = await resolve_user_circle_ban(db, updated.id)
    circle_ban = CircleBanOut(**ban_payload) if ban_payload else None
    return SessionUserResponse(
        id=updated.id,
        persona=updated.persona,
        full_name=updated.full_name,
        email=updated.email,
        mobile=updated.mobile,
        kyc_status=updated.kyc_status,
        admin_note=updated.admin_note,
        kyc_review_note=extract_kyc_review_note(updated.admin_note),
        circle_access=CircleAccessOut(**access),
        circle_ban=circle_ban,
        school_org=await _school_org_summary(db, updated),
    )


# -- ADD: /auth/token � issues a JWT for WebSocket chat auth ----------------
# The existing /auth/login endpoint above is completely untouched.
# This is the approved insertion into this file.
#
# Usage: POST /auth/token with the same email+password as /auth/login.
# Returns {"access_token": "<jwt>", "token_type": "bearer"}.
# Store in localStorage and pass as ?token=<jwt> to the WebSocket endpoint.

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")  # Brute-force protection
async def issue_token(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Issue a JWT access token for WebSocket authentication.

    Uses the same credentials as /auth/login.
    KYC must be approved to receive a token.
    """
    signup = await resolve_signup_for_credentials(
        db,
        email=body.email,
        password=body.password,
        persona=body.persona,
    )

    if not signup:
        logger.warning(f"Auth failure (/token): Account not found for email '{body.email}'")
        log = AuthAuditLog(
            email=body.email, 
            status="FAIL_EMAIL", 
            comment="Account not found in chat/token",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(log)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if signup.kyc_status != KycStatus.approved:
        logger.warning(f"Auth failure (/token): User '{body.email}' blocked due to KYC status '{signup.kyc_status}'")
        log = AuthAuditLog(
            email=body.email, 
            status="FAIL_KYC", 
            comment=f"KYC {signup.kyc_status}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(log)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KYC approval required to access chat",
        )

    log = AuthAuditLog(
        email=body.email, 
        status="SUCCESS", 
        comment=f"Token issued for chat",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    from app.services.auth_tokens import issue_token_pair

    access_token, refresh_token = await issue_token_pair(db, signup.id)
    await db.commit()
    logger.info(f"Auth success (/token): JWT issued for '{body.email}'")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def refresh_tokens(
    request: Request,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    from app.services.auth_tokens import refresh_access_token

    result = await refresh_access_token(db, body.refresh_token.strip())
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    access_token, refresh_token, _user = result
    return RefreshResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def logout(
    request: Request,
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """Revoke refresh token so it cannot be used again."""
    if not body.refresh_token:
        return None
    from app.services.auth_tokens import revoke_refresh_token

    await revoke_refresh_token(db, body.refresh_token.strip())
    return None


class FamilyHatsResponse(BaseModel):
    has_family: bool
    active_hat: str
    circle_id: Optional[str] = None
    relationship: Optional[str] = None
    student: Optional[dict[str, Any]] = None
    parent: Optional[dict[str, Any]] = None


class SwitchHatRequest(BaseModel):
    target_hat: str  # "student" | "parent"
    password: Optional[str] = None


class SwitchHatResponse(BaseModel):
    id: str
    persona: Persona
    active_hat: str
    full_name: str
    email: str
    kyc_status: KycStatus
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    circle_access: Optional[CircleAccessOut] = None
    message: str = ""


@router.get("/family-hats", response_model=FamilyHatsResponse, status_code=status.HTTP_200_OK)
async def get_family_hats(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Linked student/parent hats for same-email family accounts."""
    ctx = await build_family_hats_context(db, user)
    return FamilyHatsResponse(**ctx)


@router.post("/switch-hat", response_model=SwitchHatResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def switch_hat(
    request: Request,
    body: SwitchHatRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Switch between student and parent views on the same email account.
    Switching to parent always requires password re-entry (guardian gate).
    """
    target = (body.target_hat or "").strip().lower()
    if target not in ("student", "parent"):
        raise HTTPException(status_code=400, detail="target_hat must be 'student' or 'parent'")

    target_signup = await resolve_linked_signup(db, user, target)

    if target == "parent" and user.id != target_signup.id:
        if not body.password:
            raise HTTPException(status_code=400, detail="Password is required to switch to parent view")
        verify_password_for_hat_switch(body.password, user)

    if target == "student" and target_signup.persona == Persona.student:
        consent = await has_recorded_parental_consent(db, target_signup.id)
        if not student_hat_available(target_signup, has_parental_consent=consent):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Student view is available only with a parent or guardian present "
                    "(under 15) or after verifiable parental consent is recorded (15–17)."
                ),
            )

    from app.services.auth_tokens import issue_token_pair

    access_token, refresh_token = await issue_token_pair(db, target_signup.id)
    await db.commit()

    access = await resolve_circle_access(db, target_signup)
    active_hat = "student" if target_signup.persona == Persona.student else "parent"

    return SwitchHatResponse(
        id=target_signup.id,
        persona=target_signup.persona,
        active_hat=active_hat,
        full_name=target_signup.full_name,
        email=target_signup.email,
        kyc_status=target_signup.kyc_status,
        access_token=access_token,
        refresh_token=refresh_token,
        circle_access=CircleAccessOut(**access),
        message=f"Switched to {active_hat} view.",
    )