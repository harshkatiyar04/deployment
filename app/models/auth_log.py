from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthAuditLog(Base):
    """
    Audit log for all authentication attempts.
    Used for monitoring security and troubleshooting client login issues.
    """

    __tablename__ = "auth_audit_logs"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # SUCCESS, FAIL_EMAIL, FAIL_PASSWORD, FAIL_KYC
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Detailed reason or context
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
