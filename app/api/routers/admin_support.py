"""Admin inbox for Zenk Admin 1:1 support threads."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.db.session import get_db
from app.models.admin_support import ZenkAdminThread
from app.models.enums import KycStatus
from app.models.signup import SignupRequest
from app.services.cloudinary_service import upload_image, upload_video
from app.services.admin_support_chat import (
    admin_support_summary,
    get_thread_messages,
    list_admin_threads,
    list_support_contacts,
    open_admin_thread,
    post_thread_message,
)

router = APIRouter(
    prefix="/admin/support",
    tags=["admin-support"],
    dependencies=[Depends(require_admin_api_key)],
)


class SupportThreadOut(BaseModel):
    thread_id: str
    user_id: str
    user_name: str
    user_email: str
    user_mobile: Optional[str] = None
    persona: str
    persona_label: str
    channel_name: str
    admin_unread_count: int
    last_message_text: Optional[str] = None
    last_message_at: Optional[str] = None
    has_messages: bool = False


class SupportContactOut(BaseModel):
    user_id: str
    user_name: str
    user_email: str
    user_mobile: Optional[str] = None
    persona: str
    persona_label: str
    thread_id: Optional[str] = None
    has_thread: bool = False
    has_messages: bool = False
    admin_unread_count: int = 0


class OpenThreadRequest(BaseModel):
    user_id: str


class SupportMessageOut(BaseModel):
    id: str
    sender_role: str
    text: str
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None
    created_at: Optional[str] = None


class PostSupportMessageRequest(BaseModel):
    message: str = Field(default="", max_length=4000)
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None


class SupplierStatusRequest(BaseModel):
    decision: str = Field(..., description="approved | rejected | suspended")
    note: Optional[str] = None


class SupportSummaryOut(BaseModel):
    total_threads: int
    unread_threads: int
    unread_messages: int


SUPPORT_MEDIA_TYPES = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "video/mp4": "video",
    "video/webm": "video",
    "video/quicktime": "video",
}


@router.post("/upload")
async def support_upload_media(file: UploadFile = File(...)):
    content_type = (file.content_type or "").lower()
    if content_type not in SUPPORT_MEDIA_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Allowed: JPEG, PNG, WebP images and MP4/WebM/MOV videos.",
        )
    kind = SUPPORT_MEDIA_TYPES[content_type]
    if kind == "image":
        url = await upload_image(file, folder="zenk/support")
    else:
        url = await upload_video(file, folder="zenk/support")
    if not url:
        raise HTTPException(status_code=500, detail="Upload failed.")
    return {"url": url, "attachment_type": kind}


@router.get("/summary", response_model=SupportSummaryOut)
async def support_summary(db: AsyncSession = Depends(get_db)):
    return SupportSummaryOut(**await admin_support_summary(db))


@router.get("/contacts", response_model=list[SupportContactOut])
async def support_contacts(
    search: Optional[str] = None,
    persona: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    rows = await list_support_contacts(db, search=search, persona=persona)
    return [SupportContactOut(**r) for r in rows]


@router.post("/open", response_model=SupportThreadOut)
async def support_open_thread(body: OpenThreadRequest, db: AsyncSession = Depends(get_db)):
    try:
        row = await open_admin_thread(db, body.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return SupportThreadOut(**row)


@router.get("/threads", response_model=list[SupportThreadOut])
async def support_threads(db: AsyncSession = Depends(get_db)):
    rows = await list_admin_threads(db)
    return [SupportThreadOut(**r) for r in rows]


@router.post("/threads/by-user/{user_id}/messages", response_model=SupportMessageOut)
async def support_admin_message_to_user(
    user_id: str,
    body: PostSupportMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Open thread if needed and send admin message."""
    try:
        opened = await open_admin_thread(db, user_id)
        row = await post_thread_message(
            db,
            thread_id=opened["thread_id"],
            sender_role="admin",
            text=body.message,
            attachment_url=body.attachment_url,
            attachment_type=body.attachment_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return SupportMessageOut(**row)


@router.get("/threads/{thread_id}/messages", response_model=list[SupportMessageOut])
async def support_thread_messages(thread_id: str, db: AsyncSession = Depends(get_db)):
    rows = await get_thread_messages(db, thread_id=thread_id, mark_read_for="admin")
    await db.commit()
    return [SupportMessageOut(**r) for r in rows]


@router.post("/threads/{thread_id}/messages", response_model=SupportMessageOut)
async def support_admin_reply(
    thread_id: str,
    body: PostSupportMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await post_thread_message(
            db,
            thread_id=thread_id,
            sender_role="admin",
            text=body.message,
            attachment_url=body.attachment_url,
            attachment_type=body.attachment_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return SupportMessageOut(**row)


@router.patch("/users/{user_id}/status")
async def support_user_status(
    user_id: str,
    body: SupplierStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve, reject, or suspend a platform user (KYC gate)."""
    decision = (body.decision or "").strip().lower()
    if decision == "suspended":
        decision = "rejected"
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be approved or rejected")

    res = await db.execute(select(SignupRequest).where(SignupRequest.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.kyc_status = KycStatus.approved if decision == "approved" else KycStatus.rejected
    if body.note:
        user.admin_note = body.note.strip()
    await db.commit()
    return {
        "id": user.id,
        "kyc_status": user.kyc_status.value,
        "status": "active" if decision == "approved" else "suspended",
    }
