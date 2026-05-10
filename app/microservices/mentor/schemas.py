"""Mentor Dashboard — Pydantic Schemas."""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel


# ── Profile ───────────────────────────────────────────────────────────────────

class MentorProfileResponse(BaseModel):
    id: str
    mentor_id: str
    full_name: str
    specialty: str
    city: str
    tier: int
    tier_label: str
    assigned_circles: List[str]
    badges: List[str]
    circle_id: Optional[str] = None   # UUID of the primary circle for WebSocket chat
    # KPIs
    sessions_this_fy: int
    hours_mentored: float
    inspire_index: float
    inspire_index_percentile: int
    inspire_index_delta: float
    zenq_contribution: float
    community_uplift_count: int
    inspire_breakdown: dict



# ── Sessions ──────────────────────────────────────────────────────────────────

class MentorSessionCreate(BaseModel):
    student_circle: str
    session_date: str
    topic_area: str
    duration_hrs: float
    mode: str
    engagement_level: str
    session_notes: Optional[str] = None
    inspiration_shared: Optional[str] = None


class MentorSessionResponse(BaseModel):
    id: str
    student_circle: str
    session_date: str
    topic_area: str
    duration_hrs: float
    mode: str
    engagement_level: str
    session_notes: Optional[str]
    inspiration_shared: Optional[str]
    zenq_impact: float
    inspire_pts: float
    gross_amount: float = 0.0
    commission: float = 0.0
    net_amount: float = 0.0
    status: str = "Pending"
    created_at: str


# ── InspireIndex ──────────────────────────────────────────────────────────────

class InspireBreakdownItem(BaseModel):
    label: str
    score: float
    max_score: float
    pts_label: str


class InspireIndexResponse(BaseModel):
    total: float
    percentile: int
    delta: float
    breakdown: List[InspireBreakdownItem]
    scoring_rules: List[dict]
    kia_insight: Optional[str]


# ── Uplift Actions ────────────────────────────────────────────────────────────

class UpliftActionCreate(BaseModel):
    action_type: str  # guest_talk | career_event | resource_sharing | other
    title: str
    description: Optional[str] = None
    event_date: str


class UpliftActionResponse(BaseModel):
    id: str
    action_type: str
    title: str
    description: Optional[str]
    event_date: str
    impact_score: float
    verified: bool
    created_at: str

class AdminUpliftActionResponse(UpliftActionResponse):
    mentor_id: str
    mentor_name: str
    mentor_specialty: str


# ── Kia Chat ─────────────────────────────────────────────────────────────────

class MentorKiaChatRequest(BaseModel):
    message: str


class MentorKiaChatResponse(BaseModel):
    reply: str
    zenq_insight: Optional[str] = None


class MentorKiaMessageResponse(BaseModel):
    id: str
    mentor_id: str
    role: str
    text: str
    created_at: str


# ── Statement ─────────────────────────────────────────────────────────────────

class MentorStatementResponse(BaseModel):
    mentor_id: str
    full_name: str
    specialty: str
    fy_label: str
    total_sessions: int
    total_hours: float
    inspire_index: float
    zenq_contribution: float
    community_uplift_count: int
    sessions: List[MentorSessionResponse]
    uplift_actions: List[UpliftActionResponse]
