"""Public school invite join endpoints (no school context dependency)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cookies import access_expires_in_seconds, set_auth_cookies
from app.core.jwt_auth import get_optional_current_user
from app.db.session import get_db
from app.models.signup import SignupRequest
from app.services.auth_tokens import issue_token_pair
from app.services.school_portal_invite import accept_invite, preview_invite

join_router = APIRouter(prefix="/school/join", tags=["School Join"])


class SchoolJoinPreviewResponse(BaseModel):
    school_name: str
    school_code: str
    email: str
    display_name: str
    portal_role: str
    expires_at: str


class SchoolJoinAcceptRequest(BaseModel):
    token: str = Field(..., min_length=10)
    password: Optional[str] = Field(None, min_length=8)
    full_name: Optional[str] = Field(None, max_length=200)
    mobile: Optional[str] = Field(None, max_length=32)
    country: str = Field(default="IN", max_length=8)


class SchoolJoinAcceptResponse(BaseModel):
    status: str
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    persona: str
    full_name: str
    email: str
    session_mode: str = "cookie"
    access_expires_in: int = 0


@join_router.get("/preview", response_model=SchoolJoinPreviewResponse)
async def join_preview(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    data = await preview_invite(db, token)
    return SchoolJoinPreviewResponse(**data)


@join_router.post("/accept", response_model=SchoolJoinAcceptResponse)
async def join_accept(
    body: SchoolJoinAcceptRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[SignupRequest] = Depends(get_optional_current_user),
):
    try:
        signup, created = await accept_invite(
            db,
            token=body.token,
            password=body.password,
            full_name=body.full_name,
            mobile=body.mobile,
            country=body.country,
            current_user=current_user,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    access_token, refresh_token = await issue_token_pair(db, signup.id)
    await db.commit()

    msg = (
        "Welcome to the school portal. You can now access your dashboard."
        if created
        else "Invite accepted. Your account is linked to the school."
    )
    set_auth_cookies(response, access_token, refresh_token)
    return SchoolJoinAcceptResponse(
        status="success",
        message=msg,
        access_token=access_token,
        refresh_token=refresh_token,
        persona=str(signup.persona.value if hasattr(signup.persona, "value") else signup.persona),
        full_name=signup.full_name,
        email=signup.email,
        session_mode="cookie",
        access_expires_in=access_expires_in_seconds(),
    )
