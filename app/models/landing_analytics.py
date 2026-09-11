"""First-party marketing analytics: sessions, pageviews, CTA events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LandingSession(Base):
    __tablename__ = "landing_sessions"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    entry_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accept_language: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    screen: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    device_class: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    geo_country: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    geo_region: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    geo_city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    pageview_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LandingPageview(Base):
    __tablename__ = "landing_pageviews"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    referrer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scroll_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)


class LandingEvent(Base):
    __tablename__ = "landing_events"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    cta_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
