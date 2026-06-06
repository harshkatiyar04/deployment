"""User-facing Zenk Admin 1:1 support channel."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import get_current_user
from app.db.session import get_db
from app.models.signup import SignupRequest
from app.services.admin_support_chat import (
    get_or_create_thread,
    get_thread_messages,
    get_user_support_state,
    post_thread_message,
)
from app.services.cloudinary_service import upload_image, upload_video

router = APIRouter(prefix="/support/zenk-admin", tags=["user-support"])

SUPPORT_MEDIA_TYPES = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "video/mp4": "video",
    "video/webm": "video",
    "video/quicktime": "video",
}


class UserSupportStateOut(BaseModel):
    thread_id: str
    channel_name: str
    user_unread_count: int
    persona_label: str


class SupportMessageOut(BaseModel):
    id: str
    sender_role: str
    text: str
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None
    created_at: str | None = None


class PostUserMessageRequest(BaseModel):
    message: str = Field(default="", max_length=4000)
    attachment_url: Optional[str] = None
    attachment_type: Optional[str] = None

    @model_validator(mode="after")
    def require_content(self):
        if not (self.message or "").strip() and not (self.attachment_url or "").strip():
            raise ValueError("Message or attachment is required.")
        return self


@router.get("", response_model=UserSupportStateOut)
async def my_support_state(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_or_create_thread(db, user.id)
    await db.commit()
    state = await get_user_support_state(db, user)
    return UserSupportStateOut(**state)


@router.get("/messages", response_model=list[SupportMessageOut])
async def my_support_messages(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    thread = await get_or_create_thread(db, user.id)
    rows = await get_thread_messages(db, thread_id=thread.id, mark_read_for="user")
    await db.commit()
    return [SupportMessageOut(**r) for r in rows]


@router.post("/upload")
async def upload_support_media(
    file: UploadFile = File(...),
    user: SignupRequest = Depends(get_current_user),
):
    content_type = (file.content_type or "").lower()
    if content_type not in SUPPORT_MEDIA_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Allowed: JPEG, PNG, WebP images and MP4/WebM/MOV videos (max 25MB).",
        )
    kind = SUPPORT_MEDIA_TYPES[content_type]
    if kind == "image":
        url = await upload_image(file, folder="zenk/support")
    else:
        url = await upload_video(file, folder="zenk/support")
    if not url:
        raise HTTPException(status_code=500, detail="Upload failed. Try again.")
    return {"url": url, "attachment_type": kind}


@router.post("/messages", response_model=SupportMessageOut)
async def send_support_message(
    body: PostUserMessageRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    thread = await get_or_create_thread(db, user.id)
    try:
        row = await post_thread_message(
            db,
            thread_id=thread.id,
            sender_role="user",
            text=body.message,
            attachment_url=body.attachment_url,
            attachment_type=body.attachment_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return SupportMessageOut(**row)
