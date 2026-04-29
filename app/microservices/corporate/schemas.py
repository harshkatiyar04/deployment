"""Corporate CSR Dashboard — Pydantic Schemas."""
from typing import Optional
from pydantic import BaseModel


# ── Profile ───────────────────────────────────────────────────────────────────

class CorporateBadge(BaseModel):
    label: str
    color: str  # "gold" | "teal" | "blue"


class CorporateProfileResponse(BaseModel):
    company_name: str
    company_initials: str
    corporate_id: str
    hq_city: str
    partner_since: str
    csr_schedule: str
    badges: list[CorporateBadge]
    # KPI strip
    corporate_zenq: float
    total_csr_deployed: int
    circles_funded: int
    employees_engaged: int
    unallocated: int
    fy_label: str


# ── ZenQ Overview ─────────────────────────────────────────────────────────────

class ZenQTrendPoint(BaseModel):
    month: str
    corporate_score: float
    national_avg: float


class ZenQOverviewResponse(BaseModel):
    weighted_score: float
    tier: str           # "Gold" | "Platinum" | "Silver"
    tier_next: str      # "Platinum"
    points_to_next: int
    formula_breakdown: str
    growth_pct: int
    trend: list[ZenQTrendPoint]
    national_avg: float
    insight: str


# ── Allocations ───────────────────────────────────────────────────────────────

class CircleAllocation(BaseModel):
    circle_name: str
    leader_name: str
    leader_city: str
    allocation_pct: int
    amount: int
    zenq_score: Optional[float] = None
    status: str  # "active" | "pending"
    color: str


class AllocationResponse(BaseModel):
    total_csr: int
    unallocated: int
    circles: list[CircleAllocation]
    platform_fee_note: str


# ── Circle Performance ────────────────────────────────────────────────────────

class CirclePerformanceRow(BaseModel):
    circle_name: str
    leader: str
    city: str
    zenq_score: float
    rank: int
    participation_pct: int
    members: int
    students: int
    monthly_trend: list[float]
    status: str


class CirclePerformanceResponse(BaseModel):
    circles: list[CirclePerformanceRow]
    summary: str


# ── Employee Engagement ───────────────────────────────────────────────────────

class EngagementMetric(BaseModel):
    label: str
    value: str
    delta: str
    trend: str  # "up" | "down" | "neutral"


class TopContributor(BaseModel):
    name: str
    initials: str
    department: str
    hours: int
    impact_score: float


class EmployeeEngagementResponse(BaseModel):
    total_enrolled: int
    active_this_month: int
    circles_participating: int
    avg_hours_per_employee: float
    metrics: list[EngagementMetric]
    top_contributors: list[TopContributor]
    monthly_hours: list[dict]


# ── CSR Account ───────────────────────────────────────────────────────────────

class CSRTransaction(BaseModel):
    date: str
    description: str
    category: str
    amount: int
    type: str  # "credit" | "debit"
    circle: Optional[str] = None


class CSRAccountResponse(BaseModel):
    total_deployed: int
    total_received: int
    balance: int
    fy_label: str
    spend_by_category: list[dict]
    transactions: list[CSRTransaction]


# ── Reallocation ──────────────────────────────────────────────────────────────

class ReallocationItem(BaseModel):
    circle_name: str
    amount: int


class ReallocationRequest(BaseModel):
    allocations: list[ReallocationItem]
    fiscal_year: str


class ReallocationResponse(BaseModel):
    success: bool
    message: str
    new_unallocated: int
