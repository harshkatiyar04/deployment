from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import KycStatus, Persona


class SignupRequest(Base):
    """
    Stores signup info per persona + current KYC status.
    KYC document metadata (path) is stored here for now.
    """

    __tablename__ = "signup_requests"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))

    persona: Mapped[Persona] = mapped_column(Enum(Persona, name="persona_enum", schema="ZENK"), nullable=False)

    # Common mandatory fields
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    mobile: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # Hashed password
    address_line1: Mapped[str] = mapped_column(String(300), nullable=False)
    address_line2: Mapped[str] = mapped_column(String(300), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(120), nullable=False)
    pincode: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)

    # Sponsor fields
    sponsor_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # individual|company
    pan_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    company_registration_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    gst_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    authorized_signatory_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    authorized_signatory_designation: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    # Vendor fields
    business_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    business_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    product_categories: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # comma-separated
    website: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Student fields
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    school_or_college_name: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    grade_or_year: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    guardian_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    guardian_mobile: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # KYC
    kyc_status: Mapped[KycStatus] = mapped_column(
        Enum(KycStatus, name="kyc_status_enum", schema="ZENK"),
        nullable=False,
        default=KycStatus.pending,
    )
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    documents: Mapped[list["KycDocument"]] = relationship(
        back_populates="signup",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class KycDocument(Base):
    __tablename__ = "kyc_documents"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    signup_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey('ZENK.signup_requests.id', ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    signup: Mapped[SignupRequest] = relationship(back_populates="documents")


