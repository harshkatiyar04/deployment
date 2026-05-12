from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, String, Float, Integer, DateTime, Boolean, Text, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SchoolProfile(Base):
    __tablename__ = "school_profiles"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    school_name: Mapped[str] = mapped_column(String(300), nullable=False)
    school_code: Mapped[str] = mapped_column(String(50), nullable=False, default="ZNK-SCH-0000-000")
    affiliation: Mapped[str] = mapped_column(String(100), nullable=False, default="CBSE")
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=False)
    principal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    partner_since: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_partner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fy_current: Mapped[str] = mapped_column(String(20), nullable=False, default="2025-26")

    total_enrolled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_attendance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_academic_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    next_zqa_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reports_pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SchoolStudent(Base):
    __tablename__ = "school_students"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    school_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.school_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    grade: Mapped[str] = mapped_column(String(50), nullable=False)
    circle_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.sponsor_circles.id", ondelete="SET NULL"),
        nullable=True,
    )
    circle_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    attendance_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zqa_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="Low")
    q_report_status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")
    tutor_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tutor_recommendation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    
    # New fields for deep dive
    zenk_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dob: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    class_teacher: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sl_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mentor_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rank_in_class: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    class_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    zenq_contribution: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    zqa_baseline_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class SchoolReport(Base):
    __tablename__ = "school_reports"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    school_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.school_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.school_students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    fy: Mapped[str] = mapped_column(String(20), nullable=False, default="2025-26")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    kia_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class SchoolAttendance(Base):
    __tablename__ = "school_attendance"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.school_students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    attendance_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    working_days: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    days_present: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SchoolKiaMessage(Base):
    __tablename__ = "school_kia_messages"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    school_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.school_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class SchoolKiaWelcome(Base):
    __tablename__ = "school_kia_welcome"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.school_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    welcome_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    welcome_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_list: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class SchoolStudentSubjectScore(Base):
    __tablename__ = "school_student_subject_scores"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("ZENK.school_students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)


class SchoolStudentBloomsAssessment(Base):
    __tablename__ = "school_student_blooms_assessments"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("ZENK.school_students.id", ondelete="CASCADE"), nullable=False, index=True)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    remember: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    understand: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    apply: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    analyse: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evaluate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    create: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    assessed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class SchoolStudentSEL(Base):
    __tablename__ = "school_student_sel"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("ZENK.school_students.id", ondelete="CASCADE"), nullable=False, index=True)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    self_awareness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    self_management: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    social_awareness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    relationship_skills: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    responsible_decisions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class SchoolStudentNarrative(Base):
    __tablename__ = "school_student_narratives"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("ZENK.school_students.id", ondelete="CASCADE"), nullable=False, index=True)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    teacher_name: Mapped[str] = mapped_column(String(100), nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
