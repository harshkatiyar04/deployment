"""Notification endpoints for in-app notifications."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_api_key
from app.core.jwt_auth import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.signup import SignupRequest
from app.schemas.notification import NotificationListResponse, NotificationOut, MarkReadRequest

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)


def _notification_out(n: Notification, **extra) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        notification_type=n.notification_type,
        title=n.title,
        message=n.message,
        related_entity_id=n.related_entity_id,
        related_entity_type=n.related_entity_type,
        is_read=n.is_read,
        read_at=n.read_at.isoformat() if n.read_at else None,
        created_at=n.created_at.isoformat() if n.created_at else None,
        **extra,
    )


@router.get("/user/{user_id}", response_model=NotificationListResponse)
async def get_user_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notifications for the authenticated user only."""
    if user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your notifications")

    query = select(Notification).where(
        Notification.recipient_id == user_id,
        Notification.recipient_type == "user",
    )

    if unread_only:
        query = query.where(Notification.is_read == False)

    query = query.order_by(Notification.created_at.desc()).limit(limit)

    res = await db.execute(query)
    notifications = res.scalars().all()

    unread_res = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.recipient_id == user_id,
            Notification.recipient_type == "user",
            Notification.is_read == False,
        )
    )
    unread_count = unread_res.scalar_one() or 0

    return NotificationListResponse(
        notifications=[_notification_out(n) for n in notifications],
        unread_count=unread_count,
    )


@router.get("/admin", response_model=NotificationListResponse, dependencies=[Depends(require_admin_api_key)])
async def get_admin_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get notifications for platform admin (admin session or API key)."""
    query = select(Notification).where(
        Notification.recipient_type == "admin",
    )

    if unread_only:
        query = query.where(Notification.is_read == False)

    query = query.order_by(Notification.created_at.desc()).limit(limit)

    res = await db.execute(query)
    notifications = res.scalars().all()

    unread_res = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.recipient_type == "admin",
            Notification.is_read == False,
        )
    )
    unread_count = unread_res.scalar_one() or 0

    notification_list = []
    for n in notifications:
        current_kyc_status = None
        admin_note = None

        if n.related_entity_type == "signup" and n.related_entity_id:
            signup_res = await db.execute(
                select(SignupRequest).where(SignupRequest.id == n.related_entity_id)
            )
            signup = signup_res.scalar_one_or_none()
            if signup:
                current_kyc_status = signup.kyc_status.value if signup.kyc_status else None
                admin_note = signup.admin_note

        notification_list.append(
            _notification_out(
                n,
                current_kyc_status=current_kyc_status,
                admin_note=admin_note,
            )
        )

    return NotificationListResponse(
        notifications=notification_list,
        unread_count=unread_count,
    )


@router.post("/mark-read")
async def mark_notifications_read(
    body: MarkReadRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark the current user's notifications as read."""
    if not body.notification_ids:
        raise HTTPException(status_code=400, detail="At least one notification ID is required")

    res = await db.execute(
        select(Notification).where(Notification.id.in_(body.notification_ids))
    )
    notifications = res.scalars().all()

    if len(notifications) != len(body.notification_ids):
        raise HTTPException(status_code=404, detail="One or more notifications not found")

    for notification in notifications:
        if notification.recipient_type != "user" or notification.recipient_id != user.id:
            raise HTTPException(status_code=403, detail="Cannot mark another user's notifications")

    now = datetime.utcnow()
    for notification in notifications:
        notification.is_read = True
        notification.read_at = now

    await db.commit()

    return {"message": f"Marked {len(notifications)} notification(s) as read"}


@router.post("/admin/mark-read", dependencies=[Depends(require_admin_api_key)])
async def mark_admin_notifications_read(
    body: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
):
    """Mark platform admin notifications as read."""
    if not body.notification_ids:
        raise HTTPException(status_code=400, detail="At least one notification ID is required")

    res = await db.execute(
        select(Notification).where(Notification.id.in_(body.notification_ids))
    )
    notifications = res.scalars().all()

    if len(notifications) != len(body.notification_ids):
        raise HTTPException(status_code=404, detail="One or more notifications not found")

    for notification in notifications:
        if notification.recipient_type != "admin":
            raise HTTPException(status_code=403, detail="Not an admin notification")

    now = datetime.utcnow()
    for notification in notifications:
        notification.is_read = True
        notification.read_at = now

    await db.commit()

    return {"message": f"Marked {len(notifications)} notification(s) as read"}


@router.post("/mark-all-read/user/{user_id}")
async def mark_all_user_notifications_read(
    user_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for the authenticated user."""
    if user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your notifications")

    res = await db.execute(
        select(Notification).where(
            Notification.recipient_id == user_id,
            Notification.recipient_type == "user",
            Notification.is_read == False,
        )
    )
    notifications = res.scalars().all()

    now = datetime.utcnow()
    for notification in notifications:
        notification.is_read = True
        notification.read_at = now

    await db.commit()

    return {"message": f"Marked {len(notifications)} notification(s) as read"}


@router.post("/mark-all-read/admin", dependencies=[Depends(require_admin_api_key)])
async def mark_all_admin_notifications_read(
    db: AsyncSession = Depends(get_db),
):
    """Mark all admin notifications as read."""
    res = await db.execute(
        select(Notification).where(
            Notification.recipient_type == "admin",
            Notification.is_read == False,
        )
    )
    notifications = res.scalars().all()

    now = datetime.utcnow()
    for notification in notifications:
        notification.is_read = True
        notification.read_at = now

    await db.commit()

    return {"message": f"Marked {len(notifications)} notification(s) as read"}
