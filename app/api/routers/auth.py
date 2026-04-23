"""Authentication endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import KycStatus, Persona
from app.models.signup import SignupRequest
from app.core.security import verify_password
from app.models.auth_log import AuthAuditLog

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    email: str
    password: str
    persona: Optional[Persona] = None  # Optional: if not provided, search across all personas


class LoginResponse(BaseModel):
    id: str
    persona: Persona
    full_name: str
    email: EmailStr
    mobile: str
    kyc_status: KycStatus
    message: str


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
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
    # Build query based on whether persona is provided
    if body.persona:
        query = select(SignupRequest).where(
            SignupRequest.email == body.email,
            SignupRequest.persona == body.persona,
        )
    else:
        query = select(SignupRequest).where(SignupRequest.email == body.email)
    
    res = await db.execute(query)
    signup = res.scalar_one_or_none()
    
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
    
    # Verify password
    if not verify_password(body.password, signup.password_hash):
        logger.warning(f"Auth failure (/login): Incorrect password attempt for email '{body.email}'")
        log = AuthAuditLog(
            email=body.email, 
            status="FAIL_PASSWORD", 
            comment="Incorrect password",
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
    status_message = "Login successful"
    if signup.kyc_status == KycStatus.pending:
        status_message = "Login successful. Your KYC is pending approval."
    elif signup.kyc_status == KycStatus.rejected:
        status_message = "Login successful. Your KYC has been rejected. Please contact support."
    
    log = AuthAuditLog(
        email=body.email, 
        status="SUCCESS", 
        comment=f"Persona: {signup.persona}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log)
    await db.commit()
    
    return LoginResponse(
        id=signup.id,
        persona=signup.persona,
        full_name=signup.full_name,
        email=signup.email,
        mobile=signup.mobile,
        kyc_status=signup.kyc_status,
        message=status_message,
    )



# -- ADD: /auth/token � issues a JWT for WebSocket chat auth ----------------
# The existing /auth/login endpoint above is completely untouched.
# This is the approved insertion into this file.
#
# Usage: POST /auth/token with the same email+password as /auth/login.
# Returns {"access_token": "<jwt>", "token_type": "bearer"}.
# Store in localStorage and pass as ?token=<jwt> to the WebSocket endpoint.

from app.core.jwt_auth import create_access_token  # noqa: E402


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
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
    if body.persona:
        query = select(SignupRequest).where(
            SignupRequest.email == body.email,
            SignupRequest.persona == body.persona,
        )
    else:
        query = select(SignupRequest).where(SignupRequest.email == body.email)

    res = await db.execute(query)
    signup = res.scalar_one_or_none()

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

    if not verify_password(body.password, signup.password_hash):
        logger.warning(f"Auth failure (/token): Incorrect password attempt for email '{body.email}'")
        log = AuthAuditLog(
            email=body.email, 
            status="FAIL_PASSWORD", 
            comment="Incorrect password in chat/token",
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
    await db.commit()

    logger.info(f"Auth success (/token): JWT issued for '{body.email}'")
    token = create_access_token(data={"sub": signup.id})
    return TokenResponse(access_token=token)