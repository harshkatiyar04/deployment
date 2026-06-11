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


async def notify_circle_leaders_member_application(
    *,
    circle_id: str,
    member_signup_id: str,
    member_name: str,
    member_email: str,
    db: AsyncSession,
) -> None:
    """Tell circle leaders that someone applied via their invite link."""
    from sqlalchemy import select

    from app.chat.models import CircleMember, SponsorCircle
    from app.services.circle_budget import LEADER_ROLES

    circle_res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
    circle = circle_res.scalar_one_or_none()
    circle_label = circle.name if circle else "your circle"

    leaders_res = await db.execute(
        select(CircleMember.user_id).where(
            CircleMember.circle_id == circle_id,
            CircleMember.role.in_(list(LEADER_ROLES)),
        )
    )
    leader_ids = [row[0] for row in leaders_res.all()]
    if not leader_ids:
        logger.info(
            "No leaders to notify for circle_id=%s (member signup %s)",
            circle_id,
            member_signup_id,
        )
        return

    for leader_id in leader_ids:
        if leader_id == member_signup_id:
            continue
        await create_notification(
            recipient_id=leader_id,
            recipient_type="user",
            notification_type="circle_member_application",
            title="New circle member application",
            message=(
                f"{member_name} ({member_email}) applied to join {circle_label} "
                "using your invite link. They appear in Pending while Zenk completes verification."
            ),
            related_entity_id=member_signup_id,
            related_entity_type="signup",
            db=db,
        )


async def notify_user_leader_circle_decision(
    *,
    member_signup_id: str,
    member_name: str,
    circle_name: str,
    approved: bool,
    db: AsyncSession,
) -> None:
    if approved:
        title = "Welcome to the circle"
        message = (
            f"Your circle leader approved your membership in {circle_name}. "
            "You can now participate in circle activities."
        )
        ntype = "circle_member_approved"
    else:
        title = "Circle membership update"
        message = (
            f"Your request to join {circle_name} was not accepted by the circle leader. "
            "Contact your leader or Zenk support if you have questions."
        )
        ntype = "circle_member_rejected"
    await create_notification(
        recipient_id=member_signup_id,
        recipient_type="user",
        notification_type=ntype,
        title=title,
        message=message,
        related_entity_id=member_signup_id,
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


async def notify_user_kyc_info_required(
    *,
    signup_id: str,
    full_name: str,
    persona: str,
    admin_note: Optional[str],
    db: AsyncSession,
) -> None:
    """Create user notification when admin needs more KYC documents."""
    note_text = f" {admin_note}" if admin_note else ""
    await create_notification(
        recipient_id=signup_id,
        recipient_type="user",
        notification_type="kyc_info_required",
        title="Additional documents required",
        message=(
            f"Hello {full_name}, we need more information to complete your {persona} verification."
            f"{note_text} Sign in and upload the requested documents from your verification page."
        ),
        related_entity_id=signup_id,
        related_entity_type="signup",
        db=db,
    )

