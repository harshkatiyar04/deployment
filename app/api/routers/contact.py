"""Public landing-page contact form + survey/visit beacons (no auth)."""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.services.landing_contact import run_inquiry_followups_background
from app.services.landing_contact_store import create_landing_contact_inquiry
from app.services.landing_feedback_store import (
    create_landing_feedback,
    create_landing_visit,
)
from app.services.landing_visitor_meta import collect_visitor_meta

router = APIRouter(prefix="/contact", tags=["contact"])
logger = logging.getLogger(__name__)


class VisitorMetaIn(BaseModel):
    session_id: Optional[str] = Field(default=None, max_length=64)
    referrer: Optional[str] = Field(default=None, max_length=2000)
    landing_path: Optional[str] = Field(default=None, max_length=500)
    utm_source: Optional[str] = Field(default=None, max_length=120)
    utm_medium: Optional[str] = Field(default=None, max_length=120)
    utm_campaign: Optional[str] = Field(default=None, max_length=120)
    timezone: Optional[str] = Field(default=None, max_length=80)
    screen: Optional[str] = Field(default=None, max_length=40)
    user_agent: Optional[str] = Field(default=None, max_length=2000)


class LandingContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    interest: str = Field(min_length=1, max_length=120)
    message: str = Field(default="", max_length=4000)
    source: Optional[str] = Field(default=None, max_length=40)
    visitor: Optional[VisitorMetaIn] = None


class LandingContactOut(BaseModel):
    ok: bool = True
    message: str = "Thank you — we'll be in touch shortly."
    thank_you_sent: bool = False


class LandingFeedbackIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    interest: str = Field(min_length=1, max_length=120)
    found_via: Optional[str] = Field(default=None, max_length=120)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    algorithm_clarity: Optional[str] = Field(default=None, max_length=80)
    most_useful_signal: Optional[str] = Field(default=None, max_length=120)
    trust_for_decisions: Optional[str] = Field(default=None, max_length=120)
    suggestion: str = Field(default="", max_length=4000)
    mailing_list_opt_in: bool = True
    visitor: Optional[VisitorMetaIn] = None


class LandingFeedbackOut(BaseModel):
    ok: bool = True
    message: str = "Thank you — your feedback helps us build better."


class LandingVisitIn(BaseModel):
    visitor: VisitorMetaIn


class LandingVisitOut(BaseModel):
    ok: bool = True
    recorded: bool = False


@router.post("/inquiry", response_model=LandingContactOut, status_code=status.HTTP_200_OK)
@limiter.limit("8/hour")
async def submit_landing_contact(
    request: Request,
    background_tasks: BackgroundTasks,
    inquiry: LandingContactIn = Body(...),
    db: AsyncSession = Depends(get_db),
) -> LandingContactOut:
    name = inquiry.name.strip()
    email = str(inquiry.email).strip()
    interest = inquiry.interest.strip()
    message = (inquiry.message or "").strip()
    visitor_payload = inquiry.visitor.model_dump() if inquiry.visitor else {}
    raw_source = (inquiry.source or "").strip().lower()
    if raw_source in ("waitlist_interest", "waitlist", "interest"):
        source = "waitlist_interest"
    elif "waitlist interest form" in message.lower() or "/login" in (
        (visitor_payload.get("landing_path") or "").lower()
    ):
        source = "waitlist_interest"
    else:
        source = "landing_contact"

    try:
        meta = await collect_visitor_meta(request, client_meta=visitor_payload)
        row = await create_landing_contact_inquiry(
            db,
            name=name,
            email=email,
            interest=interest,
            message=message,
            visitor_meta=meta,
            source=source,
        )
    except Exception as exc:
        logger.exception("Landing contact save failed for email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="We could not save your message right now. Please try again or email info@zenkimpact.com.",
        ) from exc

    # Emails + flag updates run after the client gets success (SMTP was blocking the form).
    background_tasks.add_task(
        run_inquiry_followups_background,
        inquiry_id=row.id,
        name=name,
        email=email,
        interest=interest,
        message=message,
        visitor_meta=meta,
        source=source,
    )

    return LandingContactOut(
        thank_you_sent=source == "waitlist_interest",
        message=(
            "You're on the list — a confirmation is on its way to your inbox."
            if source == "waitlist_interest"
            else "Thank you — we'll be in touch shortly."
        ),
    )


@router.post("/feedback", response_model=LandingFeedbackOut, status_code=status.HTTP_200_OK)
@limiter.limit("12/hour")
async def submit_landing_feedback(
    request: Request,
    payload: LandingFeedbackIn = Body(...),
    db: AsyncSession = Depends(get_db),
) -> LandingFeedbackOut:
    """Survey + mailing list from landing popup. Separate from /inquiry."""
    name = payload.name.strip()
    email = str(payload.email).strip()
    interest = payload.interest.strip()
    visitor_payload = payload.visitor.model_dump() if payload.visitor else {}

    try:
        meta = await collect_visitor_meta(request, client_meta=visitor_payload)
        await create_landing_feedback(
            db,
            name=name,
            email=email,
            interest=interest,
            found_via=payload.found_via,
            rating=payload.rating,
            algorithm_clarity=payload.algorithm_clarity,
            most_useful_signal=payload.most_useful_signal,
            trust_for_decisions=payload.trust_for_decisions,
            suggestion=payload.suggestion or "",
            mailing_list_opt_in=payload.mailing_list_opt_in,
            visitor_meta=meta,
        )
    except Exception as exc:
        logger.exception("Landing feedback save failed for email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="We could not save your feedback right now. Please try again.",
        ) from exc

    return LandingFeedbackOut()


@router.post("/visit", response_model=LandingVisitOut, status_code=status.HTTP_200_OK)
@limiter.limit("120/hour")
async def record_landing_visit(
    request: Request,
    payload: LandingVisitIn = Body(...),
    db: AsyncSession = Depends(get_db),
) -> LandingVisitOut:
    """Light anonymous visit beacon (once per session/day)."""
    try:
        meta = await collect_visitor_meta(
            request, client_meta=payload.visitor.model_dump()
        )
        row = await create_landing_visit(db, visitor_meta=meta)
        return LandingVisitOut(recorded=bool(row))
    except Exception:
        logger.exception("Landing visit beacon failed")
        return LandingVisitOut(recorded=False)
