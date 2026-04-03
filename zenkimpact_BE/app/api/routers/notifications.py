"""Notification endpoints for in-app notifications."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.notification import Notification
from app.models.signup import SignupRequest
from app.schemas.notification import NotificationListResponse, NotificationOut, MarkReadRequest

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)


@router.get("/user/{user_id}", response_model=NotificationListResponse)
async def get_user_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Get notifications for a user (by signup_id).
    
    Query params:
    - unread_only: If true, return only unread notifications
    - limit: Maximum number of notifications to return (default: 50)
    """
    query = select(Notification).where(
        Notification.recipient_id == user_id,
        Notification.recipient_type == "user",
    )
    
    if unread_only:
        query = query.where(Notification.is_read == False)
    
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    
    res = await db.execute(query)
    notifications = res.scalars().all()
    
    # Get unread count
    unread_res = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.recipient_id == user_id,
            Notification.recipient_type == "user",
            Notification.is_read == False,
        )
    )
    unread_count = unread_res.scalar_one() or 0
    
    return NotificationListResponse(
        notifications=[
            NotificationOut(
                id=n.id,
                notification_type=n.notification_type,
                title=n.title,
                message=n.message,
                related_entity_id=n.related_entity_id,
                related_entity_type=n.related_entity_type,
                is_read=n.is_read,
                read_at=n.read_at.isoformat() if n.read_at else None,
                created_at=n.created_at.isoformat() if n.created_at else None,
            )
            for n in notifications
        ],
        unread_count=unread_count,
    )


@router.get("/admin", response_model=NotificationListResponse)
async def get_admin_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Get notifications for admin.
    
    Query params:
    - unread_only: If true, return only unread notifications
    - limit: Maximum number of notifications to return (default: 50)
    """
    query = select(Notification).where(
        Notification.recipient_type == "admin",
    )
    
    if unread_only:
        query = query.where(Notification.is_read == False)
    
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    
    res = await db.execute(query)
    notifications = res.scalars().all()
    
    # Get unread count
    unread_res = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.recipient_type == "admin",
            Notification.is_read == False,
        )
    )
    unread_count = unread_res.scalar_one() or 0
    
    # Build notification list with current status
    notification_list = []
    for n in notifications:
        current_kyc_status = None
        admin_note = None
        
        # If this is a signup-related notification, fetch current status
        if n.related_entity_type == "signup" and n.related_entity_id:
            signup_res = await db.execute(
                select(SignupRequest).where(SignupRequest.id == n.related_entity_id)
            )
            signup = signup_res.scalar_one_or_none()
            if signup:
                current_kyc_status = signup.kyc_status.value if signup.kyc_status else None
                admin_note = signup.admin_note
        
        notification_list.append(
            NotificationOut(
                id=n.id,
                notification_type=n.notification_type,
                title=n.title,
                message=n.message,
                related_entity_id=n.related_entity_id,
                related_entity_type=n.related_entity_type,
                is_read=n.is_read,
                read_at=n.read_at.isoformat() if n.read_at else None,
                created_at=n.created_at.isoformat() if n.created_at else None,
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
    db: AsyncSession = Depends(get_db),
):
    """Mark one or more notifications as read."""
    if not body.notification_ids:
        raise HTTPException(status_code=400, detail="At least one notification ID is required")
    
    res = await db.execute(
        select(Notification).where(Notification.id.in_(body.notification_ids))
    )
    notifications = res.scalars().all()
    
    if len(notifications) != len(body.notification_ids):
        raise HTTPException(status_code=404, detail="One or more notifications not found")
    
    now = datetime.utcnow()
    for notification in notifications:
        notification.is_read = True
        notification.read_at = now
    
    await db.commit()
    
    return {"message": f"Marked {len(notifications)} notification(s) as read"}


@router.post("/mark-all-read/user/{user_id}")
async def mark_all_user_notifications_read(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for a user."""
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


@router.post("/mark-all-read/admin")
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

