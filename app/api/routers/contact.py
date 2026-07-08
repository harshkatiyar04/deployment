"""Public landing-page contact form (no auth)."""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.services.landing_contact import notify_landing_contact_inquiry
from app.services.landing_contact_store import (
    create_landing_contact_inquiry,
    mark_inquiry_email_notified,
)

router = APIRouter(prefix="/contact", tags=["contact"])
logger = logging.getLogger(__name__)


class LandingContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    interest: str = Field(min_length=1, max_length=120)
    message: str = Field(default="", max_length=4000)


class LandingContactOut(BaseModel):
    ok: bool = True
    message: str = "Thank you — we'll be in touch shortly."


@router.post("/inquiry", response_model=LandingContactOut, status_code=status.HTTP_200_OK)
@limiter.limit("8/hour")
async def submit_landing_contact(
    request: Request,
    inquiry: LandingContactIn = Body(...),
    db: AsyncSession = Depends(get_db),
) -> LandingContactOut:
    name = inquiry.name.strip()
    email = str(inquiry.email).strip()
    interest = inquiry.interest.strip()
    message = (inquiry.message or "").strip()

    try:
        row = await create_landing_contact_inquiry(
            db,
            name=name,
            email=email,
            interest=interest,
            message=message,
        )
    except Exception as exc:
        logger.exception("Landing contact save failed for email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="We could not save your message right now. Please try again or email info@zenkimpact.com.",
        ) from exc

    notified = await notify_landing_contact_inquiry(
        name=name,
        email=email,
        interest=interest,
        message=message,
    )
    if notified:
        try:
            await mark_inquiry_email_notified(db, row.id)
        except Exception:
            logger.exception("Landing contact email_notified flag update failed id=%s", row.id)

    return LandingContactOut()
