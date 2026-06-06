"""Circle invite tokens, student cart submissions, and admin approval requests."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any, List, Optional

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

REQUEST_MEMBER_REMOVAL = "member_removal"
REQUEST_MEMBER_LIMIT = "member_limit_increase"
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
DEFAULT_MEMBER_LIMIT = 5
MAX_MEMBER_LIMIT = 25


class CartSubmissionStatus(str, enum.Enum):
    pending_leader = "pending_leader"
    approved = "approved"
    rejected = "rejected"


class CircleInviteToken(Base):
    __tablename__ = "circle_invite_tokens"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class CircleStudentCartSubmission(Base):
    __tablename__ = "circle_student_cart_submissions"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    submitted_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=CartSubmissionStatus.pending_leader.value
    )
    items_json: Mapped[List[Any]] = mapped_column(JSONB, nullable=False, default=list)
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    circle_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class CircleAdminRequest(Base):
    __tablename__ = "circle_admin_requests"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    request_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_PENDING)
    requested_by_user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    requested_by_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    target_user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    target_user_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    current_member_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_member_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    requested_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    leader_comment: Mapped[str] = mapped_column(Text, nullable=False)
    admin_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by_admin: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


PAYEE_CATEGORIES = frozenset(
    {"school_fees", "supplies", "books", "uniform", "other"}
)
DISBURSEMENT_PENDING = "pending"
DISBURSEMENT_PROCESSING = "processing"
DISBURSEMENT_PAID = "paid"
DISBURSEMENT_FAILED = "failed"
DISBURSEMENT_CANCELLED = "cancelled"


class CirclePayee(Base):
    __tablename__ = "circle_payees"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    beneficiary_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    bank_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    account_number: Mapped[str] = mapped_column(String(32), nullable=False)
    ifsc: Mapped[str] = mapped_column(String(16), nullable=False)
    upi_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class CircleDisbursement(Base):
    __tablename__ = "circle_disbursements"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    payee_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    amount_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=DISBURSEMENT_PENDING)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gateway_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="icici")
    gateway_session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    gateway_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class CircleSchoolPartnerMessage(Base):
    __tablename__ = "circle_school_partner_messages"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    school_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    sender_side: Mapped[str] = mapped_column(String(16), nullable=False)
    sender_signup_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    sender_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
