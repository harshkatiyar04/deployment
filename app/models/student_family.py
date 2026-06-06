from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentFamilyLink(Base):
    """Links a student signup row to a parent (sponsor_member) signup row — same email, two hats."""

    __tablename__ = "student_family_links"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    student_signup_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_signup_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship: Mapped[str] = mapped_column(String(50), nullable=False, default="parent")
    circle_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.sponsor_circles.id", ondelete="SET NULL"),
        nullable=True,
    )
    school_student_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class ParentAcademicSubmission(Base):
    """Parent-uploaded marks/transcripts — principal approval in school portal (Phase 5)."""

    __tablename__ = "parent_academic_submissions"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    parent_signup_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_signup_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    school_student_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False, default="marksheet")
    submission_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="file")
    file_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    parent_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    grade_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_principal")
    principal_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
