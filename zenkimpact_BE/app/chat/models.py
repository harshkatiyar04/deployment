"""Chat system SQLAlchemy models — all in ZENK schema."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base




class ChannelType(str, enum.Enum):
    persistent = "persistent"
    stage = "stage"




class SponsorCircle(Base):
    """A sponsor circle groups sponsors, mentors, and students together."""

    __tablename__ = "sponsor_circles"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    members: Mapped[list["CircleMember"]] = relationship(back_populates="circle")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="circle")
    channels: Mapped[list["ChatChannel"]] = relationship(back_populates="circle")




class CircleMember(Base):
    """Links a SignupRequest user to a SponsorCircle with a role."""

    __tablename__ = "circle_members"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    circle_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.sponsor_circles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # role: "lead" | "sponsor" | "mentor" | "student"
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="sponsor")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    circle: Mapped["SponsorCircle"] = relationship(back_populates="members")




class Enrollment(Base):
    """Student enrollment in a SponsorCircle."""

    __tablename__ = "enrollments"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    circle_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.sponsor_circles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    circle: Mapped["SponsorCircle"] = relationship(back_populates="enrollments")


# GamifiedPersona

class GamifiedPersona(Base):
    """
    Maps a real user to an anonymous chat persona.
    This join must NEVER appear in any sponsor-facing query or response.
    user_id must never be exposed over WebSocket or REST to sponsors/students.
    """

    __tablename__ = "gamified_personas"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_key: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="persona")
    sos_reports_filed: Mapped[list["SOSReport"]] = relationship(
        back_populates="reporter_persona",
        foreign_keys="[SOSReport.reporter_persona_id]",
    )


class ChatChannel(Base):
    __tablename__ = "chat_channels"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    circle_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.sponsor_circles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    channel_type: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, name="channel_type_enum", schema="ZENK"),
        nullable=False,
        default=ChannelType.persistent,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    circle: Mapped["SponsorCircle"] = relationship(back_populates="channels")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="channel")


# ChatMessage  — append-only in application code (no UPDATE, no DELETE ever)

class ChatMessage(Base):
    """
    Append-only chat message store.
    - gamified_persona_id is used instead of user_id to preserve anonymity.
    - hidden_at is the only mutable field (for SOS soft-hide).
    - NO updated_at.
    """

    __tablename__ = "chat_messages"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    channel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.chat_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gamified_persona_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.gamified_personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    shield_action: Mapped[str] = mapped_column(String(20), nullable=False, default="allow")
    shield_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_edited: Mapped[bool] = mapped_column(default=False, nullable=False)
    # SOS soft-hide: only this field is ever updated on a message
    hidden_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # User-triggered soft-delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    channel: Mapped["ChatChannel"] = relationship(back_populates="messages")
    persona: Mapped["GamifiedPersona"] = relationship(back_populates="messages")
    sos_reports: Mapped[list["SOSReport"]] = relationship(back_populates="message")


class SOSReport(Base):
    __tablename__ = "sos_reports"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    message_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.chat_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reporter_persona_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.gamified_personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hidden_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    admin_notified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    message: Mapped["ChatMessage"] = relationship(back_populates="sos_reports")
    reporter_persona: Mapped["GamifiedPersona"] = relationship(
        back_populates="sos_reports_filed",
        foreign_keys=[reporter_persona_id],
    )


class ChatBan(Base):
    """Tracks users who are banned from specific sponsor circles."""

    __tablename__ = "chat_bans"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    circle_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.sponsor_circles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    banned_by_admin_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reported_message_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AdminAccessLog(Base):
    """Audit trail for sensitive admin actions, tracked via PostgreSQL Trigger."""

    __tablename__ = "admin_access_log"
    __table_args__ = {"schema": "audit"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    admin_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_table: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    changes_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
