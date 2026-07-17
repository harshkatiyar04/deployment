"""Admin inbox for website contact inquiries + landing feedback."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.services.landing_contact_store import (
    get_landing_contact_inquiry,
    landing_contact_summary,
    list_landing_contact_inquiries,
    mark_landing_contact_inquiry_read,
)
from app.services.landing_feedback_store import (
    get_landing_feedback,
    landing_feedback_summary,
    list_landing_feedback,
    mark_landing_feedback_read,
)

router = APIRouter(
    prefix="/admin/website-inquiries",
    tags=["admin-website-inquiries"],
    dependencies=[Depends(require_admin_api_key)],
)


class WebsiteInquirySummaryOut(BaseModel):
    total: int
    unread: int
    feedback_total: int = 0
    feedback_unread: int = 0


class WebsiteInquiryOut(BaseModel):
    id: str
    name: str
    email: str
    interest: str
    message: str
    admin_read: bool
    email_notified: bool
    created_at: Optional[str] = None


class WebsiteFeedbackOut(BaseModel):
    id: str
    name: str
    email: str
    interest: str
    found_via: Optional[str] = None
    rating: Optional[int] = None
    suggestion: str = ""
    mailing_list_opt_in: bool = False
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    accept_language: Optional[str] = None
    referrer: Optional[str] = None
    landing_path: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    timezone: Optional[str] = None
    screen: Optional[str] = None
    geo_country: Optional[str] = None
    geo_region: Optional[str] = None
    geo_city: Optional[str] = None
    source: str = "landing_popup"
    admin_read: bool = False
    created_at: Optional[str] = None


@router.get("/summary", response_model=WebsiteInquirySummaryOut)
async def website_inquiries_summary(db: AsyncSession = Depends(get_db)):
    contact = await landing_contact_summary(db)
    feedback = await landing_feedback_summary(db)
    return WebsiteInquirySummaryOut(**contact, **feedback)


@router.get("/feedback", response_model=list[WebsiteFeedbackOut])
async def website_feedback_list(
    search: Optional[str] = None,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    rows = await list_landing_feedback(db, search=search, unread_only=unread_only)
    return [WebsiteFeedbackOut(**row) for row in rows]


@router.get("/feedback/{feedback_id}", response_model=WebsiteFeedbackOut)
async def website_feedback_detail(
    feedback_id: str,
    db: AsyncSession = Depends(get_db),
):
    row = await get_landing_feedback(db, feedback_id)
    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return WebsiteFeedbackOut(**row)


@router.post("/feedback/{feedback_id}/read", response_model=WebsiteFeedbackOut)
async def website_feedback_mark_read(
    feedback_id: str,
    db: AsyncSession = Depends(get_db),
):
    row = await mark_landing_feedback_read(db, feedback_id)
    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return WebsiteFeedbackOut(**row)


@router.get("", response_model=list[WebsiteInquiryOut])
async def website_inquiries_list(
    search: Optional[str] = None,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    rows = await list_landing_contact_inquiries(
        db, search=search, unread_only=unread_only
    )
    return [WebsiteInquiryOut(**row) for row in rows]


@router.get("/{inquiry_id}", response_model=WebsiteInquiryOut)
async def website_inquiry_detail(
    inquiry_id: str,
    db: AsyncSession = Depends(get_db),
):
    row = await get_landing_contact_inquiry(db, inquiry_id)
    if not row:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return WebsiteInquiryOut(**row)


@router.post("/{inquiry_id}/read", response_model=WebsiteInquiryOut)
async def website_inquiry_mark_read(
    inquiry_id: str,
    db: AsyncSession = Depends(get_db),
):
    row = await mark_landing_contact_inquiry_read(db, inquiry_id)
    if not row:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return WebsiteInquiryOut(**row)
