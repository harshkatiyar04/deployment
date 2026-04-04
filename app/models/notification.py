"""Notification models for in-app notifications."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationType(str, enum.Enum):
    """Types of notifications."""
    kyc_approved = "kyc_approved"
    kyc_rejected = "kyc_rejected"
    kyc_pending = "kyc_pending"
    admin_alert = "admin_alert"


class Notification(Base):
    """In-app notifications for users and admins."""

    __tablename__ = "notifications"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    
    # Recipient (signup_id for users, or "admin" for admin notifications)
    recipient_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    recipient_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "user" or "admin"
    
    # Notification details
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Related entity (e.g., signup_id for KYC notifications)
    related_entity_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    related_entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "signup", etc.
    
    # Status
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


