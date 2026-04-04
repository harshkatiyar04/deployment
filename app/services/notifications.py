"""Notification service for creating in-app notifications."""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification

logger = logging.getLogger(__name__)


async def create_notification(
    *,
    recipient_id: str,
    recipient_type: str,  # "user" or "admin"
    notification_type: str,
    title: str,
    message: str,
    related_entity_id: Optional[str] = None,
    related_entity_type: Optional[str] = None,
    db: AsyncSession,
) -> Notification:
    """Create a new in-app notification."""
    notification = Notification(
        recipient_id=recipient_id,
        recipient_type=recipient_type,
        notification_type=notification_type,
        title=title,
        message=message,
        related_entity_id=related_entity_id,
        related_entity_type=related_entity_type,
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    logger.info("Created notification: id=%s, type=%s, recipient=%s", notification.id, notification_type, recipient_id)
    return notification


async def notify_admin_new_signup(
    *,
    signup_id: str,
    persona: str,
    full_name: str,
    email: str,
    db: AsyncSession,
) -> None:
    """Create admin notification for new signup."""
    await create_notification(
        recipient_id="admin",
        recipient_type="admin",
        notification_type="kyc_pending",
        title=f"New {persona.capitalize()} Registration",
        message=f"{full_name} ({email}) has registered and is awaiting KYC approval.",
        related_entity_id=signup_id,
        related_entity_type="signup",
        db=db,
    )


async def notify_user_kyc_approved(
    *,
    signup_id: str,
    full_name: str,
    persona: str,
    db: AsyncSession,
) -> None:
    """Create user notification for KYC approval."""
    await create_notification(
        recipient_id=signup_id,
        recipient_type="user",
        notification_type="kyc_approved",
        title="KYC Approved! 🎉",
        message=f"Congratulations {full_name}! Your {persona} registration has been approved. You can now access all features.",
        related_entity_id=signup_id,
        related_entity_type="signup",
        db=db,
    )


async def notify_user_kyc_rejected(
    *,
    signup_id: str,
    full_name: str,
    persona: str,
    admin_note: Optional[str],
    db: AsyncSession,
) -> None:
    """Create user notification for KYC rejection."""
    note_text = f" Note: {admin_note}" if admin_note else ""
    await create_notification(
        recipient_id=signup_id,
        recipient_type="user",
        notification_type="kyc_rejected",
        title="KYC Rejected",
        message=f"Your {persona} registration has been rejected.{note_text} Please contact support for assistance.",
        related_entity_id=signup_id,
        related_entity_type="signup",
        db=db,
    )

