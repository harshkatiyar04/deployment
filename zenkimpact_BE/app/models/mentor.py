"""Mentor Dashboard — SQLAlchemy Models."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, String, Float, Integer, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MentorProfile(Base):
    """
    Persistent profile and aggregate KPIs for a Mentor.
    One row per mentor user account.
    """
    __tablename__ = "mentor_profiles"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    mentor_id: Mapped[str] = mapped_column(String(50), nullable=False, default="ZNK-MEN-0000-000")
    specialty: Mapped[str] = mapped_column(String(200), nullable=False, default="Technology & career mentoring")
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Bengaluru")
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tier_label: Mapped[str] = mapped_column(String(50), nullable=False, default="Tier 1 — Rising")

    # KPIs (aggregated / updated on each session log)
    sessions_this_fy: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hours_mentored: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    inspire_index: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    inspire_index_percentile: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inspire_index_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zenq_contribution: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    community_uplift_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # InspireIndex breakdown (5 axes — stored as JSON for flexibility)
    inspire_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    # Assigned circles list
    assigned_circles: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # Badges earned
    badges: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # Kia cached insight (refreshed on each InspireIndex view)
    kia_insight: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Assigned circle (nullable)
    circle_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.sponsor_circles.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class MentorSession(Base):
    """
    A single mentoring session logged by a mentor.
    """
    __tablename__ = "mentor_sessions"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    mentor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.mentor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_circle: Mapped[str] = mapped_column(String(200), nullable=False)
    session_date: Mapped[str] = mapped_column(String(20), nullable=False)  # ISO date string
    topic_area: Mapped[str] = mapped_column(String(200), nullable=False)
    duration_hrs: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    mode: Mapped[str] = mapped_column(String(100), nullable=False, default="ZenK Circle Chat video call")
    engagement_level: Mapped[str] = mapped_column(String(100), nullable=False, default="Engaged")
    session_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inspiration_shared: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Computed impact (updated on save)
    zenq_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    inspire_pts: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class MentorUpliftAction(Base):
    """
    A community uplift action performed by a mentor (guest talk, career event, resource sharing, etc.)
    """
    __tablename__ = "mentor_uplift_actions"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    mentor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.mentor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "guest_talk", "career_event", "resource_sharing"
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_date: Mapped[str] = mapped_column(String(20), nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class MentorKiaMessage(Base):
    """
    Persistent chat history for a Mentor and Kia AI Copilot.
    """
    __tablename__ = "mentor_kia_messages"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    mentor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.mentor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # "user" or "kia"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
