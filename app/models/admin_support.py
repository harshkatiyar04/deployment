"""One-to-one Zenk Admin support threads (user ↔ platform admin)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ZENK_ADMIN_CHANNEL_NAME = "Zenk Admin"


class ZenkAdminThread(Base):
    __tablename__ = "zenk_admin_threads"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    admin_unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_message_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class ZenkAdminMessage(Base):
    __tablename__ = "zenk_admin_messages"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    thread_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.zenk_admin_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_role: Mapped[str] = mapped_column(String(10), nullable=False)  # user | admin
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attachment_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachment_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
