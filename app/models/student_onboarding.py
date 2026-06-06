from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentSchoolInterest(Base):
    __tablename__ = "student_school_interests"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    student_signup_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    school_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_principal")
    principal_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    school_student_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class StudentCircleInterestRequest(Base):
    __tablename__ = "student_circle_interest_requests"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    student_signup_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    help_comment: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_leader")
    leader_signup_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    leader_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pseudonym: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    probe_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class StudentProbeMessage(Base):
    __tablename__ = "student_probe_messages"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    interest_request_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_signup_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
