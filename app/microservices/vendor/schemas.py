"""Pydantic validation schemas for the Vendor microservice."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.microservices.vendor.models import (
    OrderStatus,
    RequestPriority,
    RequestStatus,
)


# ── Product Schemas ──────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=300)
    sku: Optional[str] = Field(None, max_length=64)
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    mrp: float = Field(..., gt=0)
    student_price: Optional[float] = Field(None, gt=0)
    student_discount: int = Field(0, ge=0, le=100)
    member_discount: int = Field(10, ge=0, le=100)
    stock_quantity: int = Field(0, ge=0)
    image_url: Optional[str] = None

    @field_validator("price")
    @classmethod
    def price_must_be_lte_mrp(cls, v, info):
        mrp = info.data.get("mrp")
        if mrp is not None and v > mrp:
            raise ValueError("Selling price cannot exceed MRP")
        return v


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=300)
    sku: Optional[str] = Field(None, max_length=64)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    mrp: Optional[float] = Field(None, gt=0)
    student_price: Optional[float] = Field(None, gt=0)
    student_discount: Optional[int] = Field(None, ge=0, le=100)
    member_discount: Optional[int] = Field(None, ge=0, le=100)
    stock_quantity: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: str
    vendor_id: str
    name: str
    sku: Optional[str]
    category: str
    description: Optional[str]
    price: float
    mrp: float
    student_price: Optional[float]
    student_discount: int
    member_discount: int
    stock_quantity: int
    image_url: Optional[str]
    is_active: bool
    # New fields for active promotions
    discounted_price: Optional[float] = None
    active_promotion_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Order Schemas ────────────────────────────────────────────────────────────

class OrderOut(BaseModel):
    id: str
    product_id: str
    vendor_id: str
    buyer_name: str
    circle_name: Optional[str]
    quantity: int
    unit_price: float
    total_amount: float
    delivery_address: Optional[str] = None
    phone_number: Optional[str] = None
    order_type: str
    payment_method: str = "UPI"
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    product_name: Optional[str] = None
    discount_amount: float = 0.0
    promotion_id: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderCreate(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1)
    unit_price: float
    total_amount: float
    vendor_id: str

class CartCheckoutRequest(BaseModel):
    items: list[OrderCreate]
    delivery_address: str = Field(..., min_length=5)
    phone_number: str = Field(..., min_length=10)
    order_type: str = Field(..., description="'student' or 'personal'")
    circle_name: Optional[str] = None


# ── Product Request Schemas ──────────────────────────────────────────────────

class ProductRequestCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    quantity_needed: int = Field(1, ge=1)
    budget_per_unit: Optional[float] = Field(None, gt=0)
    circle_name: Optional[str] = Field(None, max_length=200)
    target_audience: Optional[str] = Field(None, max_length=200)
    priority: RequestPriority = RequestPriority.medium


class ProductRequestOut(BaseModel):
    id: str
    requester_id: str
    vendor_id: Optional[str]
    title: str
    description: Optional[str]
    category: Optional[str]
    quantity_needed: int
    budget_per_unit: Optional[float]
    circle_name: Optional[str]
    target_audience: Optional[str]
    priority: RequestPriority
    status: RequestStatus
    vendor_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    requester_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ProductRequestStatusUpdate(BaseModel):
    status: RequestStatus
    vendor_notes: Optional[str] = None


# ── Dashboard Stats Schema ───────────────────────────────────────────────────

class VendorStatsOut(BaseModel):
    total_products: int
    active_products: int
    total_orders: int
    total_revenue: float
    pending_orders: int
    pending_requests: int
    orders_this_month: int
    revenue_this_month: float
    revenue_trend: list[dict] = []
    orders_by_status: dict = {}
    unread_notifications: int = 0


# ── Settings & Promotion Schemas ─────────────────────────────────────────────

class VendorSettingsUpdate(BaseModel):
    full_name: Optional[str] = None
    business_name: Optional[str] = None
    email_notifications: Optional[bool] = None
    sms_alerts: Optional[bool] = None
    auto_accept_orders: Optional[bool] = None
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    monthly_revenue_target: Optional[float] = Field(None, ge=0)


class VendorSettingsOut(BaseModel):
    id: str
    vendor_id: str
    full_name: str
    business_name: str
    email_notifications: bool
    sms_alerts: bool
    auto_accept_orders: bool
    low_stock_threshold: int
    monthly_revenue_target: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class VendorPromotionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    discount_percentage: float
    start_date: datetime
    end_date: datetime
    scope: str = "all"
    target_product_ids: list[str] = []
    target_audience: str = "all" # all, student, sponsor


class VendorPromotionOut(BaseModel):
    id: str
    vendor_id: str
    title: str
    description: Optional[str]
    discount_percentage: float
    start_date: datetime
    end_date: datetime
    is_active: bool
    scope: str
    target_product_ids: list[str] = []
    target_product_names: list[str] = []
    target_audience: str = "all"
    created_at: datetime
    expires_in_hours: Optional[int] = None

    @field_validator("target_product_ids", mode="before")
    @classmethod
    def parse_product_ids(cls, v):
        if isinstance(v, str):
            return [id.strip() for id in v.split(",") if id.strip()]
        return v or []

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: str
    recipient_id: str
    notification_type: str
    title: str
    message: str
    related_entity_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
