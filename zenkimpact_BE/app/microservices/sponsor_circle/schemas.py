from pydantic import BaseModel
from typing import List


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
    balance_to_spend: int
    fy_label: str
    transactions: List[Transaction]


class Member(BaseModel):
    name: str
    initials: str
    participation_pct: int
    badge: str


class ParticipationResponse(BaseModel):
    members: List[Member]
    circle_avg_pct: int
    leader_name: str
    leader_pct: int


class StudentUpdateResponse(BaseModel):
    student_name: str
    maths_score: int
    maths_baseline: int
    science_score: int
    science_baseline: int
    attendance_pct: int
    improvement_pts: int
    school_comment: str


class TimeImpactResponse(BaseModel):
    total_hrs_all_circles: int
    total_circles_count: int
    highest_circle_hrs: float
    highest_circle_name: str
    my_circle_hrs: float


class CircleRankRow(BaseModel):
    rank: int
    name: str
    zenq: int
    city: str
    is_mine: bool


class RankingsResponse(BaseModel):
    circles: List[CircleRankRow]


class KiaInsightResponse(BaseModel):
    analysis: str
    suggestion: str
    coordinator_name: str
