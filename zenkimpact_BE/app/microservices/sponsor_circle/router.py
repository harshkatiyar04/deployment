from fastapi import APIRouter
from app.microservices.sponsor_circle.schemas import (
    SummaryResponse,
    BudgetResponse,
    Transaction,
    ParticipationResponse,
    Member,
    StudentUpdateResponse,
    TimeImpactResponse,
    RankingsResponse,
    CircleRankRow,
    KiaInsightResponse,
)
from app.services.kia import generate_budget_insight

router = APIRouter(prefix="/sponsor-circle", tags=["Sponsor Circle Dashboard"])


@router.get("/summary", response_model=SummaryResponse)
async def get_summary():
    return SummaryResponse(
        zenq_score=82,
        circle_rank=3,
        total_circles=47,
        participation_pct=74,
        circle_avg_pct=68,
        time_this_month_hrs=6.5,
        top_group_hrs=11.2,
        zenq_change=4,
        rank_previous=5,
    )


@router.get("/budget", response_model=BudgetResponse)
async def get_budget():
    return BudgetResponse(
        total_budget=150000,
        spent=94200,
        collected=124500,
        balance_to_spend=55800,
        fy_label="FY 2025-26",
        transactions=[
            Transaction(date="Mar 20", description="New Member Kit", amount=5000, category="Operational"),
            Transaction(date="Mar 15", description="Kia AI Tokens", amount=3500, category="Platform"),
            Transaction(date="Mar 10", description="School Supplies", amount=12000, category="Student"),
        ],
    )


@router.get("/participation", response_model=ParticipationResponse)
async def get_participation():
    return ParticipationResponse(
        members=[
            Member(name="Rohit Chawla", initials="RC", participation_pct=94, badge="top"),
            Member(name="Priya Sharma", initials="PS", participation_pct=74, badge="you"),
            Member(name="Arjun Kulkarni", initials="AK", participation_pct=70, badge=""),
            Member(name="Sneha Mehta", initials="SM", participation_pct=64, badge=""),
            Member(name="Vikram Patil", initials="VP", participation_pct=60, badge=""),
            Member(name="Mrs. Devika", initials="MD", participation_pct=46, badge=""),
        ],
        circle_avg_pct=68,
        leader_name="Rohit Chawla",
        leader_pct=94,
    )


@router.get("/student-update", response_model=StudentUpdateResponse)
async def get_student_update():
    return StudentUpdateResponse(
        student_name="Ananya D.",
        maths_score=84,
        maths_baseline=61,
        science_score=78,
        science_baseline=55,
        attendance_pct=92,
        improvement_pts=23,
        school_comment="Ananya is asking about entering a district-level science competition. Excellent engagement this term.",
    )


@router.get("/time-impact", response_model=TimeImpactResponse)
async def get_time_impact():
    return TimeImpactResponse(
        total_hrs_all_circles=847,
        total_circles_count=47,
        highest_circle_hrs=11.2,
        highest_circle_name="Vasundhara Circle, Pune",
        my_circle_hrs=6.5,
    )


@router.get("/rankings", response_model=RankingsResponse)
async def get_rankings():
    return RankingsResponse(
        circles=[
            CircleRankRow(rank=1, name="Vasundhara Circle", zenq=96, city="Pune", is_mine=False),
            CircleRankRow(rank=2, name="Prarambh Mumbai", zenq=89, city="Mumbai", is_mine=False),
            CircleRankRow(rank=3, name="Ashoka Rising", zenq=82, city="Mumbai", is_mine=True),
            CircleRankRow(rank=4, name="Udaan Bangalore", zenq=78, city="Bengaluru", is_mine=False),
            CircleRankRow(rank=5, name="Kishore Circle", zenq=71, city="Delhi", is_mine=False),
        ]
    )


@router.get("/budget-insight", response_model=KiaInsightResponse)
async def get_budget_insight():
    # 1. Fetch current budget data (usually from DB, using mock values for now)
    budget_data = {
        "total_budget": 150000,
        "spent": 94200,
        "collected": 124500,
        "balance_to_spend": 55800,
        "fy_label": "FY 2025-26",
    }
    
    # 2. Call Kia service to analyze the data
    insight = await generate_budget_insight(budget_data)
    
    return KiaInsightResponse(
        analysis=insight.get("analysis", ""),
        suggestion=insight.get("suggestion", ""),
        coordinator_name=insight.get("coordinator_name", "Rohit")
    )
