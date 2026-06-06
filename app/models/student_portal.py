from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentKiaMessage(Base):
    __tablename__ = "student_kia_messages"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    student_signup_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class StudentMentoringThread(Base):
    __tablename__ = "student_mentoring_threads"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    student_signup_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    circle_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.sponsor_circles.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Circle mentoring")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class StudentMentoringMessage(Base):
    __tablename__ = "student_mentoring_messages"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    thread_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.student_mentoring_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_signup_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_role: Mapped[str] = mapped_column(String(30), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
