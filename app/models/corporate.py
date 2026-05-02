from __future__ import annotations
from typing import Optional
from sqlalchemy import ForeignKey, String, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class CorporateProfile(Base):
    """
    Persistent state for the Corporate CSR Dashboard.
    Stores KPI aggregates and dynamic lists for nested dashboard tools.
    """
    __tablename__ = "corporate_profiles"
    __table_args__ = {"schema": "ZENK"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("ZENK.signup_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_initials: Mapped[str] = mapped_column(String(50), nullable=False)
    hq_city: Mapped[str] = mapped_column(String(100), nullable=False)
    partner_since: Mapped[str] = mapped_column(String(50), nullable=False, default="Apr 2024")
    csr_schedule: Mapped[str] = mapped_column(String(255), nullable=False, default="CSR Schedule VII — Item (ii): Education")
    brand_color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="#0284C7")

    # KPIs
    corporate_zenq: Mapped[float] = mapped_column(Float, nullable=False, default=78.4)
    total_csr_deployed: Mapped[int] = mapped_column(Integer, nullable=False, default=100000)
    circles_funded: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    employees_engaged: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    unallocated: Mapped[int] = mapped_column(Integer, nullable=False, default=20000)
    fy_label: Mapped[str] = mapped_column(String(50), nullable=False, default="FY 2025-26")

    # JSON collections for nested state
    badges: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    zenq_trend: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    circle_allocations: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    circle_performance: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    engagement_metrics: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    top_contributors: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    spend_by_category: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    transactions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    monthly_burn: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    alerts: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    upcoming_disbursements: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    corporate_goals: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    strategy_brief: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    industry_sector: Mapped[str] = mapped_column(String(100), nullable=False, default="Technology sector")

    # Employee engagement enrichment
    volunteers: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    employee_circles: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    engagement_schemes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    department_breakdown: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    monthly_hours: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    kia_engagement_insight: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    active_this_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_hours_per_employee: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    zenq_lift_from_staff: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

