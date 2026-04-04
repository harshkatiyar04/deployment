"""Notification schemas."""
from typing import Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    notification_type: str
    title: str
    message: str
    related_entity_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    is_read: bool
    read_at: Optional[str] = None
    created_at: str
    # Current status (for signup-related notifications)
    current_kyc_status: Optional[str] = None  # Current status from signup_requests table
    admin_note: Optional[str] = None  # Current admin note from signup_requests table


class NotificationListResponse(BaseModel):
    notifications: list[NotificationOut]
    unread_count: int


class MarkReadRequest(BaseModel):
    notification_ids: list[str]

