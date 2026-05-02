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
    brand_color: str = "#0284C7"
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

class CircleMilestone(BaseModel):
    month: str
    event: str

class CircleVolunteer(BaseModel):
    name: str
    initials: str
    hours_per_month: float

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
    # New rich fields
    kia_insight: Optional[str] = None
    zenq_start: float = 60.0
    fund_utilised_pct: int = 75
    next_disbursement: Optional[str] = None
    volunteers: list[dict] = []
    milestones: list[dict] = []
    risk_flag: Optional[str] = None
    predicted_zenq_by_fy_end: Optional[float] = None
    student_zqa: Optional[float] = None
    allocation_amount: Optional[int] = None
    allocation_pct: Optional[int] = None
    color: str = "#00D4BE"


class CirclePerformanceResponse(BaseModel):
    circles: list[CirclePerformanceRow]
    summary: str
    platform_pool_amount: int = 0
    platform_pool_pct: int = 10
    national_avg_zenq: float = 76.2
    total_circles_benefitting: int = 47


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
    circle: Optional[str] = None
    zenq_contribution: Optional[float] = None
    badge: Optional[str] = None  # "gold" | "silver" | "bronze"


class EmployeeCircle(BaseModel):
    name: str
    employees: int
    company_match: int
    zenq: float
    rank: int
    fund: int


class EngagementScheme(BaseModel):
    icon: str
    title: str
    description: str
    participants: int
    total_matched: Optional[int] = None
    zenq_uplift: Optional[float] = None
    status: str
    extra: Optional[str] = None


class DepartmentEngagement(BaseModel):
    department: str
    employees: int
    active: int
    hours: int


class EmployeeEngagementResponse(BaseModel):
    total_enrolled: int
    active_this_month: int
    circles_participating: int
    avg_hours_per_employee: float
    zenq_lift_from_staff: float = 0.0
    metrics: list[EngagementMetric]
    top_contributors: list[TopContributor]
    monthly_hours: list[dict]
    volunteers: list[TopContributor] = []
    employee_circles: list[EmployeeCircle] = []
    engagement_schemes: list[EngagementScheme] = []
    department_breakdown: list[DepartmentEngagement] = []
    kia_insight: Optional[str] = None


# ── CSR Account ───────────────────────────────────────────────────────────────

class CSRTransaction(BaseModel):
    date: str
    description: str
    category: str
    amount: int
    type: str  # "credit" | "debit" | "interest"
    circle: Optional[str] = None
    running_balance: Optional[int] = None
    reference: Optional[str] = None


class UpcomingDisbursement(BaseModel):
    circle_name: str
    amount: int
    due_date: str
    status: str  # "scheduled" | "pending_approval" | "disbursed"
    tranche: str


class CSRAccountResponse(BaseModel):
    total_deployed: int
    total_received: int
    balance: int
    committed: int = 0
    allocated: int = 0
    unallocated: int = 0
    fy_label: str
    account_number: str = "ZNK-CORP-0000-00"
    mandate_amount: int = 0
    mandate_used_pct: float = 0.0
    escrow_interest_earned: int = 0
    compliance_status: str = "on_track"  # "on_track" | "at_risk" | "overdue"
    spend_by_category: list[dict]
    transactions: list[CSRTransaction]
    upcoming_disbursements: list[UpcomingDisbursement] = []
    monthly_burn: list[dict] = []  # [{month, amount}]
    alerts: list[dict] = []



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
