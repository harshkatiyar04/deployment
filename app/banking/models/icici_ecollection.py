"""ICICI eCollection MH7 — VAN registry, events, and idempotent transactions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

TXN_PENDING_VALIDATE = "pending_validate"
TXN_ACCEPTED = "accepted"
TXN_REJECTED = "rejected"
TXN_CREDITED = "credited"

EVENT_VALIDATE = "validate"
EVENT_CREDIT_CONFIRM = "credit_confirm"


class EcollectionVan(Base):
    """Virtual Account Number mapped to a circle (and optional member)."""

    __tablename__ = "ecollection_vans"
    __table_args__ = (
        UniqueConstraint("van", name="uq_ecollection_van"),
        {"schema": "ZENK"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_code: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    van_suffix: Mapped[str] = mapped_column(String(30), nullable=False)
    van: Mapped[str] = mapped_column(String(35), nullable=False)
    circle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    member_user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class EcollectionTransaction(Base):
    """One logical bank remittance — unique on (utr, amount_paise)."""

    __tablename__ = "ecollection_transactions"
    __table_args__ = (
        UniqueConstraint("utr", "amount_paise", name="uq_ecollection_utr_amount"),
        {"schema": "ZENK"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    utr: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_inr: Mapped[str] = mapped_column(String(20), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    van: Mapped[str] = mapped_column(String(35), nullable=False, index=True)
    client_code: Mapped[str] = mapped_column(String(6), nullable=False)
    payment_mode: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    remitter_name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    remitter_account: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    remitter_ifsc: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    circle_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=TXN_PENDING_VALIDATE)
    reject_reason: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    reject_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bank_tran_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    credited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ledger_posted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class EcollectionEvent(Base):
    """Raw bank webhook audit trail."""

    __tablename__ = "ecollection_events"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    event_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    utr: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    request_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    response_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    client_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
