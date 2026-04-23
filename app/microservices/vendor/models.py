"""Vendor marketplace database models."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey, Integer,
    String, Text, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class OrderStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class RequestPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    fulfilled = "fulfilled"
    rejected = "rejected"


# ── Vendor Product ───────────────────────────────────────────────────────────

class VendorProduct(Base):
    """A product listed by a vendor on the ZenK educational marketplace."""

    __tablename__ = "vendor_products"
    __table_args__ = (
        Index("ix_vendor_products_vendor_id", "vendor_id"),
        Index("ix_vendor_products_category", "category"),
        {"schema": "ZENK"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    vendor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    price: Mapped[float] = mapped_column(Float, nullable=False)
    mrp: Mapped[float] = mapped_column(Float, nullable=False)
    student_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    student_discount: Mapped[int] = mapped_column(Integer, default=0)
    member_discount: Mapped[int] = mapped_column(Integer, default=10)

    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    vendor = relationship("SignupRequest", foreign_keys=[vendor_id])
    orders = relationship("VendorOrder", back_populates="product", cascade="all, delete-orphan")


# ── Vendor Order ─────────────────────────────────────────────────────────────

class VendorOrder(Base):
    """An order placed against a vendor's product."""

    __tablename__ = "vendor_orders"
    __table_args__ = (
        Index("ix_vendor_orders_vendor_id", "vendor_id"),
        Index("ix_vendor_orders_status", "status"),
        {"schema": "ZENK"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.vendor_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    vendor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    buyer_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="SET NULL"),
        nullable=True,
    )

    buyer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    circle_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)

    delivery_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    order_type: Mapped[str] = mapped_column(String(50), nullable=False, default="personal")
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False, default="UPI")

    # Discount tracking
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    promotion_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status_enum", schema="ZENK"),
        nullable=False,
        default=OrderStatus.pending,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    product = relationship("VendorProduct", back_populates="orders")
    vendor = relationship("SignupRequest", foreign_keys=[vendor_id])


# ── Product Request (Leader → Vendor) ────────────────────────────────────────

class ProductRequest(Base):
    """A request from a Circle Leader asking the marketplace for a specific product."""

    __tablename__ = "product_requests"
    __table_args__ = (
        Index("ix_product_requests_vendor_id", "vendor_id"),
        Index("ix_product_requests_requester_id", "requester_id"),
        {"schema": "ZENK"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    requester_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    vendor_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity_needed: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    budget_per_unit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    circle_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    target_audience: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    priority: Mapped[RequestPriority] = mapped_column(
        Enum(RequestPriority, name="request_priority_enum", schema="ZENK"),
        nullable=False,
        default=RequestPriority.medium,
    )
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, name="request_status_enum", schema="ZENK"),
        nullable=False,
        default=RequestStatus.pending,
    )
    vendor_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    requester = relationship("SignupRequest", foreign_keys=[requester_id])
    vendor = relationship("SignupRequest", foreign_keys=[vendor_id])


# ── Vendor Settings ──────────────────────────────────────────────────────────

class VendorSettings(Base):
    """Configuration settings and preferences for a vendor."""

    __tablename__ = "vendor_settings"
    __table_args__ = (
        Index("ix_vendor_settings_vendor_id", "vendor_id", unique=True),
        {"schema": "ZENK"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    vendor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
    )

    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_alerts: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_accept_orders: Mapped[bool] = mapped_column(Boolean, default=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)
    monthly_revenue_target: Mapped[float] = mapped_column(Float, default=50000.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    vendor = relationship("SignupRequest")


# ── Vendor Promotion ─────────────────────────────────────────────────────────

class VendorPromotion(Base):
    """Discount campaigns created by vendors for their products."""

    __tablename__ = "vendor_promotions"
    __table_args__ = (
        Index("ix_vendor_promotions_vendor_id", "vendor_id"),
        {"schema": "ZENK"},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    vendor_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discount_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Targeting scope: "all" or "specific" (for products)
    scope: Mapped[str] = mapped_column(String(50), default="all")
    target_product_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True) 

    # Targeting audience: "all", "student", or "sponsor" (member)
    target_audience: Mapped[str] = mapped_column(String(50), default="all")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    
    vendor = relationship("SignupRequest")
