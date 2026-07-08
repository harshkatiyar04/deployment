"""Admin inbox for public website contact form submissions."""

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

router = APIRouter(
    prefix="/admin/website-inquiries",
    tags=["admin-website-inquiries"],
    dependencies=[Depends(require_admin_api_key)],
)


class WebsiteInquirySummaryOut(BaseModel):
    total: int
    unread: int


class WebsiteInquiryOut(BaseModel):
    id: str
    name: str
    email: str
    interest: str
    message: str
    admin_read: bool
    email_notified: bool
    created_at: Optional[str] = None


@router.get("/summary", response_model=WebsiteInquirySummaryOut)
async def website_inquiries_summary(db: AsyncSession = Depends(get_db)):
    return WebsiteInquirySummaryOut(**await landing_contact_summary(db))


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
