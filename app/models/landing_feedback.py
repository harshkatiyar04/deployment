"""Landing survey / mailing-list feedback and light visit beacons."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LandingFeedbackSubmission(Base):
    __tablename__ = "landing_feedback_submissions"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    interest: Mapped[str] = mapped_column(String(120), nullable=False)
    found_via: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mailing_list_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accept_language: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    landing_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    screen: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    geo_country: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    geo_region: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    geo_city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    source: Mapped[str] = mapped_column(String(40), nullable=False, default="landing_popup")
    admin_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class LandingVisit(Base):
    __tablename__ = "landing_visits"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accept_language: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    landing_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    screen: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    geo_country: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    geo_region: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    geo_city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
