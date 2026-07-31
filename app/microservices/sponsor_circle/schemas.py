from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
import re


class SummaryResponse(BaseModel):
    zenq_score: int
    circle_rank: int
    total_circles: int
    participation_pct: int
    circle_avg_pct: int
    time_this_month_hrs: float
    top_group_hrs: float
    zenq_change: int
    rank_previous: int


class Transaction(BaseModel):
    date: str
    description: str
    amount: int
    category: str


class BudgetResponse(BaseModel):
    total_budget: int
    spent: int
    collected: int
    available_balance: int = 0
    remaining_target: int = 0
    balance_to_spend: int
    fy_label: str
    fy_key: Optional[str] = "2025-26"
    circle_id: Optional[str] = None
    circle_name: Optional[str] = None
    can_set_budget: bool = False
    budget_set_at: Optional[datetime] = None
    transactions: List[Transaction]
    budget_configured: bool = False
    # Live banking fields (ICICI VAN + disbursement reservations)
    van_credited: int = 0
    reserved_in_flight: int = 0
    disbursed_paid: int = 0
    collected_live: bool = True


class SetCircleBudgetRequest(BaseModel):
    annual_budget: int = Field(..., gt=0, le=50_000_000, description="Annual budget in INR")
    fy_label: Optional[str] = Field(None, max_length=20, description="e.g. 2025-26")
    circle_id: Optional[str] = None


class Member(BaseModel):
    user_id: Optional[str] = None
    name: str
    initials: str
    participation_pct: Optional[int] = None
    badge: str = ""
    is_top: bool = False
    hours_this_month: Optional[float] = None
    messages_count: int = 0
    orders_count: int = 0
    enrollment_reviews_count: int = 0
    role: Optional[str] = None
    role_label: Optional[str] = None
    is_removable: bool = False
    pending_removal: bool = False


class SponsoredStudentSummary(BaseModel):
    pseudonym: str
    school_student_id: Optional[str] = None
    grade: Optional[str] = None
    attendance_pct: Optional[int] = None
    avg_score: Optional[int] = None
    zqa_score: Optional[int] = None
    risk_level: Optional[str] = None
    q_report_status: Optional[str] = None
    sl_name: Optional[str] = None
    class_teacher: Optional[str] = None


class ParticipationResponse(BaseModel):
    members: List[Member]
    sponsored_student: Optional[SponsoredStudentSummary] = None
    circle_avg_pct: Optional[int] = None
    leader_name: str
    leader_pct: Optional[int] = None
    circle_total_hrs: Optional[float] = None
    period_label: str = "This month"
    metrics_available: bool = False
    message: Optional[str] = None
    member_count: int = 0
    member_limit: int = 5
    is_leader: bool = False
    can_request_limit_increase: bool = False
    pending_admin_requests: int = 0


class MemberRemovalRequestBody(BaseModel):
    circle_id: Optional[str] = None
    target_user_id: str
    comment: str = Field(..., min_length=10, max_length=2000)


class MemberLimitRequestBody(BaseModel):
    circle_id: Optional[str] = None
    requested_limit: int = Field(..., ge=6, le=25)
    comment: str = Field(..., min_length=10, max_length=2000)


class CircleRenameRequestBody(BaseModel):
    circle_id: str
    new_name: str = Field(..., min_length=2, max_length=255)
    comment: str = Field(..., min_length=10, max_length=2000)


class CircleRenameStatusOut(BaseModel):
    can_request: bool
    current_name: str
    next_eligible_at: Optional[str] = None
    cooldown_days: int = 90
    pending_request: Optional["CircleAdminRequestOut"] = None
    blocked_reason: Optional[str] = None
    policy_note: str


class CircleAdminRequestOut(BaseModel):
    id: str
    circle_id: str
    circle_name: Optional[str] = None
    request_type: str
    status: str
    requested_by_name: Optional[str] = None
    target_user_name: Optional[str] = None
    current_member_count: Optional[int] = None
    current_member_limit: Optional[int] = None
    requested_limit: Optional[int] = None
    current_circle_name: Optional[str] = None
    requested_circle_name: Optional[str] = None
    leader_comment: str
    admin_comment: Optional[str] = None
    reviewed_by_admin: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: Optional[str] = None


class CircleAdminRequestCreateResponse(BaseModel):
    status: str = "success"
    message: str
    request: CircleAdminRequestOut


class PendingCircleMemberItem(BaseModel):
    id: str
    full_name: str
    email: str
    kyc_status: str
    leader_status: str = "pending"
    in_circle: bool = False
    can_approve: bool = False
    can_reject: bool = False
    created_at: Optional[datetime] = None
    # Explicit UTC ISO (…Z) for when they applied via invite — not account signup time.
    applied_at: Optional[str] = None


class PendingCircleMembersResponse(BaseModel):
    circle_id: str
    circle_name: str
    members: List[PendingCircleMemberItem]


class MemberApplicationDecisionRequest(BaseModel):
    decision: str = Field(..., description="approved or rejected")
    circle_id: Optional[str] = None


class PatchCircleNameRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class ProvisionCircleRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class StudentUpdateResponse(BaseModel):
    student_name: str
    sl_name: Optional[str] = None
    maths_score: int
    maths_baseline: int
    science_score: int
    science_baseline: int
    attendance_pct: int
    improvement_pts: int
    school_comment: str


class SponsoredSubjectScore(BaseModel):
    subject: str
    quarter: str
    score: int


class SponsoredBlooms(BaseModel):
    quarter: str
    remember: float = 0
    understand: float = 0
    apply: float = 0
    analyse: float = 0
    evaluate: float = 0
    create: float = 0


class SponsoredSEL(BaseModel):
    quarter: str
    self_awareness: float = 0
    self_management: float = 0
    social_awareness: float = 0
    relationship_skills: float = 0
    responsible_decisions: float = 0


class SponsoredNarrative(BaseModel):
    quarter: str
    teacher_name: str
    narrative: str
    finalized: bool = False


class ParentApprovedUploadBrief(BaseModel):
    document_type: str
    submission_kind: str = "file"
    approved_at: Optional[str] = None
    parent_note: Optional[str] = None
    grade_payload: Optional[dict] = None
    has_file: bool = False


class SponsoredStudentProfileResponse(BaseModel):
    pseudonym: str
    school_student_id: Optional[str] = None
    grade: Optional[str] = None
    circle_name: Optional[str] = None
    sl_name: Optional[str] = None
    class_teacher: Optional[str] = None
    mentor_name: Optional[str] = None
    attendance_pct: Optional[int] = None
    avg_score: Optional[int] = None
    zqa_score: Optional[int] = None
    risk_level: Optional[str] = None
    q_report_status: Optional[str] = None
    improvement_pts: Optional[int] = None
    zenq_contribution: Optional[float] = None
    rank_in_class: Optional[str] = None
    class_size: Optional[int] = None
    rank_display: Optional[str] = None
    quarter: Optional[str] = None
    latest_quarter: str = "Q4"
    quarter_status: str = "published"
    quarter_message: str = ""
    quarters_with_data: List[str] = []
    subject_scores: List[SponsoredSubjectScore] = []
    blooms: Optional[SponsoredBlooms] = None
    sel: Optional[SponsoredSEL] = None
    narrative: Optional[SponsoredNarrative] = None
    zqa_breakdown: Optional[dict] = None
    school_comment: str = ""
    tutor_recommendation_status: Optional[str] = None
    has_zqa: bool = False
    privacy_note: str = ""
    parent_approved_uploads: List[ParentApprovedUploadBrief] = []
    viewer: Optional[str] = None
    read_only: bool = True


class TimeImpactResponse(BaseModel):
    metrics_available: bool = False
    has_enrolled_student: bool = False
    message: Optional[str] = None
    total_hrs_all_circles: Optional[float] = None
    total_minutes_all_circles: Optional[int] = None
    total_circles_count: Optional[int] = None
    highest_circle_hrs: Optional[float] = None
    highest_circle_minutes: Optional[int] = None
    highest_circle_name: Optional[str] = None
    my_circle_hrs: Optional[float] = None
    my_circle_minutes: Optional[int] = None


class CircleRankRow(BaseModel):
    rank: int
    name: str
    zenq: int
    city: str
    is_mine: bool


class RankingsResponse(BaseModel):
    circles: List[CircleRankRow]
    platform_rankings_available: bool = False
    message: Optional[str] = None


class StatementRow(BaseModel):
    date: str
    type: str = ""
    tag: str = ""
    desc: str
    debit: str
    credit: str
    balance: str


class StatementResponse(BaseModel):
    total_budget: int
    spent: int
    collected: int
    available_balance: int = 0
    remaining_target: int = 0
    balance_to_spend: int
    fy_label: str
    circle_name: Optional[str] = None
    rows: List[StatementRow]
    has_data: bool = False
    closing_balance: Optional[int] = None
    credit_total: Optional[int] = None
    debit_total: Optional[int] = None
    ledger_ok: bool = True
    warning: Optional[str] = None


class VendorPaymentRow(BaseModel):
    id: str
    date: str
    vendor: str
    amount: int
    status: str
    category: str
    buyer_name: str = ""


class CirclePayeeResponse(BaseModel):
    id: str
    display_name: str
    beneficiary_name: str
    category: str
    category_label: str
    bank_name: Optional[str] = None
    account_masked: str
    ifsc: str
    upi_id: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


class CirclePayeeCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=200)
    beneficiary_name: str = Field(..., min_length=2, max_length=200)
    category: str = Field(default="other", pattern="^(school_fees|supplies|books|uniform|other)$")
    bank_name: Optional[str] = Field(None, max_length=120)
    account_number: str = Field(...)
    ifsc: str = Field(...)
    upi_id: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=500)
    circle_id: Optional[str] = None

    @field_validator("display_name", "beneficiary_name")
    @classmethod
    def _strip_names(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if len(cleaned) < 2:
            raise ValueError("Must be at least 2 characters")
        return cleaned

    @field_validator("bank_name")
    @classmethod
    def _strip_bank(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned or None

    @field_validator("account_number")
    @classmethod
    def _normalize_account(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v or "")
        if not re.fullmatch(r"\d{8,18}", digits):
            raise ValueError("Account number must be 8–18 digits")
        return digits

    @field_validator("ifsc")
    @classmethod
    def _normalize_ifsc(cls, v: str) -> str:
        code = re.sub(r"\s+", "", (v or "")).upper()
        if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", code):
            raise ValueError("IFSC must be 11 characters like ICIC0001234")
        return code

    @field_validator("upi_id")
    @classmethod
    def _normalize_upi(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        upi = v.strip()
        if not upi:
            return None
        if not re.fullmatch(r"[\w.\-]{2,256}@[\w.\-]{2,64}", upi, flags=re.IGNORECASE):
            raise ValueError("UPI ID must look like name@bank (e.g. school@icici)")
        return upi


class DisbursementHistoryRow(BaseModel):
    id: str
    date: str
    vendor: str
    description: str
    amount: int
    status: str
    status_key: str
    category: str
    category_key: str
    payee_id: str
    due_date: Optional[str] = None
    due_date_label: Optional[str] = None
    gateway_ref: Optional[str] = None
    paid_at: Optional[str] = None
    created_at: Optional[str] = None


class DepositRequestAlert(BaseModel):
    id: str
    amount: int
    description: str
    due_date_label: Optional[str] = None
    payee_name: str


class VendorPaymentsDashboardResponse(BaseModel):
    total_disbursed: int
    total_pending: int
    vendors_served: int
    payment_history: List[DisbursementHistoryRow]
    payees: List[CirclePayeeResponse]
    next_deposit_request: Optional[DepositRequestAlert] = None
    gateway_provider: str = "ICICI Bank"


class InitiateDisbursementRequest(BaseModel):
    payee_id: str
    amount_inr: int = Field(..., gt=0, le=5_000_000)
    description: Optional[str] = Field(None, max_length=300)
    due_date: Optional[str] = None
    circle_id: Optional[str] = None


class InitiateDisbursementResponse(BaseModel):
    disbursement_id: str
    session_id: str
    redirect_url: str
    amount_inr: int
    payee_name: str


class CompleteDisbursementRequest(BaseModel):
    session_id: str
    success: bool = True
    gateway_ref: Optional[str] = None
    circle_id: Optional[str] = None


class MemberContributionRow(BaseModel):
    name: str
    initials: str
    role: str
    total_contributed: Optional[int] = None
    this_month: Optional[int] = None
    pct: Optional[int] = None
    badge: str = ""
    zenq: Optional[float] = None
    role_label: Optional[str] = None
    kyc_name: Optional[str] = None


class UnmatchedCreditRow(BaseModel):
    remitter_name: str
    amount: int
    utr: Optional[str] = None
    payment_mode: Optional[str] = None
    credited_at: Optional[str] = None


class MemberContributionsResponse(BaseModel):
    tracking_available: bool
    members: List[MemberContributionRow]
    total_collected: Optional[int] = None
    total_budget: Optional[int] = None
    funded_pct: Optional[int] = None
    spent: int = 0
    message: str
    unmatched_total: int = 0
    attributed_total: int = 0
    credit_count: int = 0
    matched_credit_count: int = 0
    unmatched_credits: List[UnmatchedCreditRow] = []
    source: str = "icici_ecollection"


class PulseItem(BaseModel):
    id: str
    type: str
    text: str
    source: str
    time: Optional[str] = None
    summary: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None


class SponsorBadge(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    earned: bool = False
    earned_at: Optional[str] = None
    progress_current: Optional[int] = None
    progress_target: Optional[int] = None
    progress_label: Optional[str] = None


class SponsorStreak(BaseModel):
    id: str
    label: str
    current: int = 0
    unit: str = "week"
    active_this_week: bool = False
    building_this_week: bool = False
    next_milestone: Optional[int] = None
    hint: str = ""


class ProfilePulseResponse(BaseModel):
    circle_feed: List[PulseItem]
    global_feed: List[PulseItem]
    global_available: bool = False
    global_news_status: Optional[str] = None
    global_news_message: Optional[str] = None
    global_news_stale: bool = False
    badges: List[SponsorBadge] = []
    badges_available: bool = False
    badges_earned_count: int = 0
    badges_total: int = 0
    streaks: List[SponsorStreak] = []


class ImpactLeagueRow(BaseModel):
    rank: int
    circle_name: str
    impact_score: Optional[int] = None
    student_count: int = 0
    zenq_avg: Optional[int] = None
    is_mine: bool = False


class ImpactLeagueResponse(BaseModel):
    rows: List[ImpactLeagueRow]
    available: bool = False
    message: Optional[str] = None


class ImpactImprovementMonth(BaseModel):
    month: str
    us: Optional[int] = None
    top: Optional[int] = None


class ImpactImprovementResponse(BaseModel):
    available: bool = False
    message: Optional[str] = None
    months: List[ImpactImprovementMonth] = []
    summary: Optional[str] = None
    circle_name: Optional[str] = None
    show_national_benchmark: bool = False


class CircleStudentRow(BaseModel):
    id: str
    name: str
    pseudonym: Optional[str] = None
    grade: str
    attendance_pct: int
    zqa_score: Optional[int] = None
    initials: str


class SchoolPartnerResponse(BaseModel):
    school_id: str
    school_name: str
    principal_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    circle_id: str
    linked_students: int = 0
    leader_name: Optional[str] = None


class SchoolPartnerMessage(BaseModel):
    id: str
    sender_side: str
    sender_name: Optional[str] = None
    body: str
    created_at: Optional[str] = None


class SchoolPartnerMessageRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    circle_id: Optional[str] = None


class KiaInsightResponse(BaseModel):
    analysis: str
    suggestion: str
    coordinator_name: str


class CircleOverviewBudget(BaseModel):
    total_budget: int
    spent: int
    collected: int
    available_balance: int = 0
    remaining_target: int = 0
    balance_to_spend: int
    fy_label: str


class CircleOverviewResponse(BaseModel):
    circle_id: str
    circle_name: str
    is_leader: bool
    member_count: int
    student_count: int
    pending_enrollment_count: int
    zenq_score: Optional[int] = None
    zenq_available: bool = False
    zenq_source: Optional[str] = None
    zenq_breakdown: Optional[dict] = None
    zenq_scoreboard: Optional[dict] = None
    legacy_zqa_avg: Optional[int] = None
    circle_rank: Optional[int] = None
    total_circles: Optional[int] = None
    participation_pct: int = 0
    circle_avg_pct: int = 0
    participation_vs_avg: int = 0
    participation_available: bool = False
    time_this_month_hrs: Optional[float] = None
    top_group_hrs: Optional[float] = None
    zenq_change: Optional[int] = None
    rank_previous: Optional[int] = None
    budget: CircleOverviewBudget
    has_students: bool = False
    member_limit: int = 5
    onboarding_hint: Optional[str] = None


class CircleInviteLinkResponse(BaseModel):
    token: str
    invite_url: str
    expires_at: datetime
    circle_id: str
    circle_name: str
    leader_name: str = ""
    share_url: str = ""


class InviteResolveResponse(BaseModel):
    circle_id: str
    circle_name: str


class CartItemInput(BaseModel):
    product_id: str
    vendor_id: str
    quantity: int = Field(1, ge=1)
    unit_price: float = Field(..., ge=0)
    total_amount: int = Field(..., ge=0)
    product_name: Optional[str] = None


class StudentCartSubmitRequest(BaseModel):
    circle_id: Optional[str] = None
    items: List[CartItemInput]
    delivery_address: str = Field(..., min_length=5)
    phone_number: str = Field(..., min_length=10)


class StudentCartSubmissionOut(BaseModel):
    id: str
    circle_id: str
    submitted_by: str
    submitter_name: str
    status: str
    items: list
    delivery_address: str
    phone_number: str
    total_amount: int
    created_at: Optional[str] = None
    decided_at: Optional[str] = None


class StudentCartDecisionRequest(BaseModel):
    decision: str = Field(..., description="approved or rejected")
    circle_id: Optional[str] = None


class ZenqTargetAchievementRequest(BaseModel):
    sponsor_user_id: str = Field(..., min_length=8)
    target_status: str = Field(..., description="none | partial | full | stretch")
    notes: Optional[str] = Field(None, max_length=500)
    circle_id: Optional[str] = None
    quarter: Optional[str] = Field(None, max_length=10)
    fy: Optional[str] = Field(None, max_length=20)


class ZenqTargetAchievementResponse(BaseModel):
    id: str
    circle_id: str
    sponsor_user_id: str
    quarter: str
    fy: str
    target_status: str
    notes: Optional[str] = None
    created_at: Optional[str] = None
