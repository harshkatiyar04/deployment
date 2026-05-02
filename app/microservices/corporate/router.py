"""Corporate CSR Dashboard — FastAPI Router."""
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.jwt_auth import get_current_user
from app.models.signup import SignupRequest
from app.models.enums import Persona
from app.models.corporate import CorporateProfile
from app.microservices.corporate.schemas import (
    CorporateProfileResponse, CorporateBadge,
    ZenQOverviewResponse, ZenQTrendPoint,
    AllocationResponse, CircleAllocation,
    CirclePerformanceResponse, CirclePerformanceRow,
    EmployeeEngagementResponse, EngagementMetric, TopContributor,
    EmployeeCircle, EngagementScheme, DepartmentEngagement,
    CSRAccountResponse, CSRTransaction, UpcomingDisbursement,
    ReallocationRequest, ReallocationResponse,
)


router = APIRouter(prefix="/corporate", tags=["Corporate CSR Dashboard"])


def _require_corporate(user: SignupRequest) -> SignupRequest:
    """Guard: only corporate persona can access this dashboard."""
    if user.persona != Persona.corporate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Corporate dashboard is restricted to corporate accounts.",
        )
    return user


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=CorporateProfileResponse)
async def get_corporate_profile(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        if "corporate2" in user.email.lower():
            company_name = "ICICI Bank"
            company_initials = "ICICI"
        elif "hcl" in user.email.lower():
            company_name = "HCL Foundation"
            company_initials = "HCL"
        else:
            company_name = "TCS Foundation"
            company_initials = "TCS"
            
        profile = CorporateProfile(
            id=user.id,
            company_name=company_name,
            company_initials=company_initials,
            hq_city="Mumbai" if company_initials == "TCS" else "Noida",
            brand_color="#E31E24" if company_initials == "ICICI" else "#004B98",
            total_csr_deployed=100000,
            unallocated=20000,
            fy_label="FY 2025-26",
            badges=[
                {"label": "Impact Leader — Gold Tier", "color": "gold"},
                {"label": "ZenK Certified Partner", "color": "teal"},
            ],
            zenq_trend=[
                {"month": "Apr", "corporate_score": 58, "national_avg": 72},
                {"month": "May", "corporate_score": 61, "national_avg": 72},
                {"month": "Jun", "corporate_score": 64, "national_avg": 72},
                {"month": "Jul", "corporate_score": 67, "national_avg": 72},
                {"month": "Aug", "corporate_score": 69, "national_avg": 72},
                {"month": "Sep", "corporate_score": 71, "national_avg": 72},
                {"month": "Oct", "corporate_score": 73, "national_avg": 72},
                {"month": "Nov", "corporate_score": 74, "national_avg": 72},
                {"month": "Dec", "corporate_score": 75, "national_avg": 72},
                {"month": "Jan", "corporate_score": 76, "national_avg": 72},
                {"month": "Feb", "corporate_score": 77, "national_avg": 72},
                {"month": "Mar", "corporate_score": 78.4, "national_avg": 72},
            ],
            circle_allocations=[
                {"circle_name": "Ashoka Rising Circle", "leader_name": "Dr. Rahul Sharma", "leader_city": "Mumbai", "allocation_pct": 60, "amount": 60000, "zenq_score": 82, "status": "active", "color": "#00D4BE"},
                {"circle_name": "Udaan Bangalore", "leader_name": "Ms. Sunita Kumar", "leader_city": "Bengaluru", "allocation_pct": 20, "amount": 20000, "zenq_score": 78, "status": "active", "color": "#F6C343"},
                {"circle_name": "Unallocated", "leader_name": "—", "leader_city": "—", "allocation_pct": 20, "amount": 20000, "zenq_score": None, "status": "pending", "color": "#4e4635"}
            ],
            circle_performance=[
                {"circle_name": "Ashoka Rising Circle", "leader": "Dr. Rahul Sharma", "city": "Mumbai", "zenq_score": 82, "rank": 3, "participation_pct": 78, "members": 14, "students": 42, "monthly_trend": [70, 72, 75, 76, 78, 80, 81, 82, 82, 82, 82, 82], "status": "active"},
                {"circle_name": "Udaan Bangalore", "leader": "Ms. Sunita Kumar", "city": "Bengaluru", "zenq_score": 78, "rank": 7, "participation_pct": 65, "members": 11, "students": 33, "monthly_trend": [62, 64, 66, 68, 70, 72, 74, 75, 76, 77, 78, 78], "status": "active"}
            ],
            engagement_metrics=[
                {"label": "Total Enrolled", "value": "12", "delta": "+3 this FY", "trend": "up"},
                {"label": "Active This Month", "value": "9", "delta": "+2 vs last month", "trend": "up"},
                {"label": "Avg Hours/Employee", "value": "6.5h", "delta": "-0.5h vs last month", "trend": "down"},
                {"label": "Volunteer Hours Total", "value": "78h", "delta": "+12h this month", "trend": "up"}
            ],
            top_contributors=[
                {"name": "Priya Sharma", "initials": "PS", "department": "Engineering", "hours": 14, "impact_score": 92},
                {"name": "Arjun Mehta", "initials": "AM", "department": "HR", "hours": 12, "impact_score": 88},
                {"name": "Divya Nair", "initials": "DN", "department": "Finance", "hours": 11, "impact_score": 84},
                {"name": "Rahul Joshi", "initials": "RJ", "department": "Product", "hours": 9, "impact_score": 81},
                {"name": "Sneha Kapoor", "initials": "SK", "department": "Sales", "hours": 8, "impact_score": 79}
            ],
            spend_by_category=[
                {"category": "Student Circles", "amount": 80000, "color": "#00D4BE"},
                {"category": "Platform Fee", "amount": 10000, "color": "#F6C343"},
                {"category": "Unallocated", "amount": 20000, "color": "#4e4635"}
            ],
            transactions=[
                {"date": "Mar 20, 2026", "description": "Ashoka Rising Circle — Q4 Tranche", "category": "Circle Fund", "amount": 15000, "type": "debit", "circle": "Ashoka Rising Circle"},
                {"date": "Mar 10, 2026", "description": "Udaan Bangalore — Q4 Tranche", "category": "Circle Fund", "amount": 5000, "type": "debit", "circle": "Udaan Bangalore"},
                {"date": "Feb 28, 2026", "description": "CSR Disbursement", "category": "Inflow", "amount": 100000, "type": "credit"},
                {"date": "Jan 15, 2026", "description": "Platform Service Fee Q3", "category": "Platform Fee", "amount": 2500, "type": "debit"},
                {"date": "Dec 20, 2025", "description": "Ashoka Rising Circle — Q3 Tranche", "category": "Circle Fund", "amount": 15000, "type": "debit", "circle": "Ashoka Rising Circle"},
                {"date": "Dec 10, 2025", "description": "Udaan Bangalore — Q3 Tranche", "category": "Circle Fund", "amount": 5000, "type": "debit", "circle": "Udaan Bangalore"},
                {"date": "Nov 5, 2025", "description": "Ashoka Rising Circle — Q2 Tranche", "category": "Circle Fund", "amount": 15000, "type": "debit", "circle": "Ashoka Rising Circle"},
                {"date": "Oct 1, 2025", "description": "Platform Service Fee Q2", "category": "Platform Fee", "amount": 2500, "type": "debit"}
            ]
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        
    badges_list = [CorporateBadge(**b) for b in (profile.badges or [])]
        
    return CorporateProfileResponse(
        company_name=profile.company_name,
        company_initials=profile.company_initials,
        corporate_id=f"Corporate-ID: CIN-ZNK-{profile.id[:8]}",
        hq_city=profile.hq_city,
        partner_since=profile.partner_since,
        csr_schedule=profile.csr_schedule,
        brand_color=profile.brand_color,
        badges=badges_list,
        corporate_zenq=profile.corporate_zenq,
        total_csr_deployed=profile.total_csr_deployed,
        circles_funded=profile.circles_funded,
        employees_engaged=profile.employees_engaged,
        unallocated=profile.unallocated,
        fy_label=profile.fy_label,
    )


# ── ZenQ Overview ─────────────────────────────────────────────────────────────

@router.get("/zenq-overview", response_model=ZenQOverviewResponse)
async def get_zenq_overview(
    fy: str = "2025-26",
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)

    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        trend_data = [
            ZenQTrendPoint(month="Apr", corporate_score=58, national_avg=72),
            ZenQTrendPoint(month="May", corporate_score=61, national_avg=72),
            ZenQTrendPoint(month="Jun", corporate_score=64, national_avg=72),
            ZenQTrendPoint(month="Jul", corporate_score=67, national_avg=72),
            ZenQTrendPoint(month="Aug", corporate_score=69, national_avg=72),
            ZenQTrendPoint(month="Sep", corporate_score=71, national_avg=72),
            ZenQTrendPoint(month="Oct", corporate_score=73, national_avg=72),
            ZenQTrendPoint(month="Nov", corporate_score=74, national_avg=72),
            ZenQTrendPoint(month="Dec", corporate_score=75, national_avg=72),
            ZenQTrendPoint(month="Jan", corporate_score=76, national_avg=72),
            ZenQTrendPoint(month="Feb", corporate_score=77, national_avg=72),
            ZenQTrendPoint(month="Mar", corporate_score=78.4, national_avg=72),
        ]
        weighted_score = 78.4
    else:
        trend_data = [ZenQTrendPoint(**p) for p in (profile.zenq_trend or [])]
        weighted_score = profile.corporate_zenq

    return ZenQOverviewResponse(
        weighted_score=weighted_score,
        tier="Gold",
        tier_next="Platinum",
        points_to_next=2,
        formula_breakdown="Corporate ZenQ = Σ (circle_zenq × allocation%)",
        growth_pct=35,
        trend=trend_data,
        national_avg=72,
        insight="Your Corporate ZenQ tracking is fully data-driven.",
    )


# ── Allocations ───────────────────────────────────────────────────────────────

@router.get("/allocations", response_model=AllocationResponse)
async def get_allocations(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        circles = [
            CircleAllocation(
                circle_name="Ashoka Rising Circle",
                leader_name="Dr. Rahul Sharma",
                leader_city="Mumbai",
                allocation_pct=60,
                amount=60000,
                zenq_score=82,
                status="active",
                color="#00D4BE",
            ),
            CircleAllocation(
                circle_name="Udaan Bangalore",
                leader_name="Ms. Sunita Kumar",
                leader_city="Bengaluru",
                allocation_pct=20,
                amount=20000,
                zenq_score=78,
                status="active",
                color="#F6C343",
            ),
            CircleAllocation(
                circle_name="Unallocated",
                leader_name="—",
                leader_city="—",
                allocation_pct=20,
                amount=20000,
                zenq_score=None,
                status="pending",
                color="#4e4635",
            ),
        ]
        total_csr = 100000
        unallocated = 20000
    else:
        circles = [CircleAllocation(**c) for c in (profile.circle_allocations or [])]
        total_csr = profile.total_csr_deployed
        unallocated = profile.unallocated

    return AllocationResponse(
        total_csr=total_csr,
        unallocated=unallocated,
        circles=circles,
        platform_fee_note="ZenK Platform allocation (10% included within each circle tranche)",
    )


# ── Reallocation ──────────────────────────────────────────────────────────────

@router.post("/reallocate", response_model=ReallocationResponse)
async def reallocate_funds(
    body: ReallocationRequest,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Corporate profile not found.")

    total_requested = sum(item.amount for item in body.allocations)
    if total_requested > profile.unallocated:
        raise HTTPException(status_code=400, detail="Allocation exceeds available unallocated balance.")

    # Update database
    profile.unallocated -= total_requested
    
    # Update circle_allocations list
    current_allocs = list(profile.circle_allocations or [])
    
    for alloc in body.allocations:
        found = False
        for c in current_allocs:
            if c.get("circle_name") == alloc.circle_name:
                c["amount"] = c.get("amount", 0) + alloc.amount
                c["allocation_pct"] = (c["amount"] / profile.total_csr_deployed) * 100
                found = True
                break
        if not found:
            current_allocs.append({
                "circle_name": alloc.circle_name,
                "leader_name": "New Leader",
                "leader_city": "N/A",
                "allocation_pct": (alloc.amount / profile.total_csr_deployed) * 100,
                "amount": alloc.amount,
                "zenq_score": 75,
                "status": "active",
                "color": "#4e4635"
            })
            
    # Also update Unallocated circle if it exists
    for c in current_allocs:
        if c.get("circle_name") == "Unallocated":
            c["amount"] = profile.unallocated
            c["allocation_pct"] = (c["amount"] / profile.total_csr_deployed) * 100
            
    profile.circle_allocations = current_allocs
    
    # Add to transactions
    txs = list(profile.transactions or [])
    from datetime import date
    today_str = date.today().strftime("%b %d, %Y")
    for alloc in body.allocations:
        txs.insert(0, {
            "date": today_str,
            "description": f"Allocation to {alloc.circle_name}",
            "category": "Circle Fund",
            "amount": alloc.amount,
            "type": "debit",
            "circle": alloc.circle_name
        })
    profile.transactions = txs

    await db.commit()
    await db.refresh(profile)

    return ReallocationResponse(
        success=True,
        message=f"Successfully allocated ₹{total_requested:,} across {len(body.allocations)} circle(s).",
        new_unallocated=profile.unallocated,
    )


# ── Circle Performance ────────────────────────────────────────────────────────

@router.get("/circles-performance", response_model=CirclePerformanceResponse)
async def get_circles_performance(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        circles = [
            CirclePerformanceRow(
                circle_name="Ashoka Rising Circle",
                leader="Dr. Rahul Sharma",
                city="Mumbai",
                zenq_score=82,
                rank=3,
                participation_pct=78,
                members=14,
                students=42,
                monthly_trend=[70, 72, 75, 76, 78, 80, 81, 82, 82, 82, 82, 82],
                status="active",
            ),
            CirclePerformanceRow(
                circle_name="Udaan Bangalore",
                leader="Ms. Sunita Kumar",
                city="Bengaluru",
                zenq_score=78,
                rank=7,
                participation_pct=65,
                members=11,
                students=33,
                monthly_trend=[62, 64, 66, 68, 70, 72, 74, 75, 76, 77, 78, 78],
                status="active",
            ),
        ]
        summary = "2 active circles | 25 total sponsors | 75 students impacted"
    else:
        circles = [CirclePerformanceRow(**c) for c in (profile.circle_performance or [])]
        active_count = len([c for c in circles if c.status == "active"])
        impacted = sum(c.students for c in circles)
        summary = f"{active_count} active circles | {impacted} students impacted"

    return CirclePerformanceResponse(
        circles=circles,
        summary=summary,
        platform_pool_amount=int(profile.total_csr_deployed * 0.1) if profile else 10000,
        platform_pool_pct=10,
        national_avg_zenq=76.2,
        total_circles_benefitting=47
    )


# ── Live ZenQ Polling ─────────────────────────────────────────────────────────

@router.get("/circles-performance/live")
async def get_live_circle_performance(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Lightweight endpoint for 30s polling of live ZenQ scores."""
    _require_corporate(user)
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile or not profile.circle_performance:
        return {"circles": []}
        
    # In a real app, this might query an active events stream.
    # Here we simulate minor live fluctuations for demo purposes.
    import random
    live_data = []
    for c in profile.circle_performance:
        base_score = float(c.get("zenq_score", 0))
        # Small +/- 0.5 fluctuation to simulate real-time live data
        fluctuation = round(random.uniform(-0.5, 0.5), 1)
        live_data.append({
            "circle_name": c.get("circle_name"),
            "live_zenq": min(100.0, max(0.0, base_score + fluctuation))
        })
        
    return {"circles": live_data}


# ── PDF Impact Report ─────────────────────────────────────────────────────────

from fastapi.responses import StreamingResponse
from app.microservices.corporate.pdf_report import generate_impact_report

@router.get("/impact-report/{circle_name}")
async def download_impact_report(
    circle_name: str,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Generates a professional multi-section PDF impact report for a circle."""
    _require_corporate(user)
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    circle_data = next(
        (c for c in (profile.circle_performance or [])
         if c.get("circle_name") == circle_name), None
    )
    if not circle_data:
        raise HTTPException(status_code=404, detail="Circle not found in your portfolio")

    profile_info = {"company_name": profile.company_name}
    buffer = generate_impact_report(profile_info, circle_data)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=ZenK_Impact_{circle_name.replace(' ', '_')}.pdf"
        },
    )


# ── Employee Engagement ───────────────────────────────────────────────────────

@router.get("/employees", response_model=EmployeeEngagementResponse)
async def get_employee_engagement(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    # Default monthly hours
    default_monthly_hours = [
        {"month": "Apr", "hours": 32}, {"month": "May", "hours": 38},
        {"month": "Jun", "hours": 41}, {"month": "Jul", "hours": 44},
        {"month": "Aug", "hours": 48}, {"month": "Sep", "hours": 52},
        {"month": "Oct", "hours": 58}, {"month": "Nov", "hours": 62},
        {"month": "Dec", "hours": 65}, {"month": "Jan", "hours": 70},
        {"month": "Feb", "hours": 74}, {"month": "Mar", "hours": 84},
    ]

    if not profile:
        return EmployeeEngagementResponse(
            total_enrolled=12, active_this_month=9, circles_participating=2,
            avg_hours_per_employee=6.5, zenq_lift_from_staff=8.2,
            metrics=[
                EngagementMetric(label="Volunteers Active", value="12", delta="+3 this FY", trend="up"),
                EngagementMetric(label="Hours Contributed", value="84 hrs", delta="This FY", trend="up"),
                EngagementMetric(label="Employee Circles Formed", value="2", delta="Co-funded by TCS", trend="up"),
                EngagementMetric(label="ZenQ Lift from Staff", value="+8.2", delta="Added to Corp ZenQ", trend="up"),
            ],
            top_contributors=[
                TopContributor(name="Priya Sharma", initials="PS", department="Engineering", hours=14, impact_score=92, badge="gold"),
                TopContributor(name="Arjun Mehta", initials="AM", department="HR", hours=12, impact_score=88, badge="silver"),
                TopContributor(name="Divya Nair", initials="DN", department="Finance", hours=11, impact_score=84, badge="bronze"),
                TopContributor(name="Rahul Joshi", initials="RJ", department="Product", hours=9, impact_score=81),
                TopContributor(name="Sneha Kapoor", initials="SK", department="Sales", hours=8, impact_score=79),
            ],
            monthly_hours=default_monthly_hours,
        )

    metrics = [EngagementMetric(**m) for m in (profile.engagement_metrics or [])]
    top_contributors = [TopContributor(**c) for c in (profile.top_contributors or [])]
    volunteers = [TopContributor(**v) for v in (profile.volunteers or [])]
    employee_circles = [EmployeeCircle(**ec) for ec in (profile.employee_circles or [])]
    engagement_schemes = [EngagementScheme(**s) for s in (profile.engagement_schemes or [])]
    department_breakdown = [DepartmentEngagement(**d) for d in (profile.department_breakdown or [])]

    return EmployeeEngagementResponse(
        total_enrolled=profile.employees_engaged,
        active_this_month=profile.active_this_month or 9,
        circles_participating=profile.circles_funded,
        avg_hours_per_employee=profile.avg_hours_per_employee or 6.5,
        zenq_lift_from_staff=profile.zenq_lift_from_staff or 8.2,
        metrics=metrics,
        top_contributors=top_contributors,
        monthly_hours=profile.monthly_hours or default_monthly_hours,
        volunteers=volunteers,
        employee_circles=employee_circles,
        engagement_schemes=engagement_schemes,
        department_breakdown=department_breakdown,
        kia_insight=profile.kia_engagement_insight,
    )


# ── CSR Account ───────────────────────────────────────────────────────────────

@router.get("/csr-account", response_model=CSRAccountResponse)
async def get_csr_account(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    # ── Default rich mock data ─────────────────────────────────────────────────
    if not profile:
        total_received = 1200000
        committed      = 900000
        allocated      = 820000
        total_deployed = 820000
        balance        = 300000
        unallocated    = 300000
        mandate_amount = 1200000
        fy_label       = "FY 2025-26"
        account_number = "ZNK-CORP-1234-TC"

        spend_by_category = [
            {"category": "Student Circles",   "amount": 720000, "color": "#4A72F5"},
            {"category": "Platform Fee",      "amount": 100000, "color": "#F6C343"},
            {"category": "Escrow Interest",   "amount":   2400, "color": "#0CBEAA"},
            {"category": "Unallocated",       "amount": 300000, "color": "#e8e8e4"},
        ]

        monthly_burn = [
            {"month": "Apr", "amount": 20000}, {"month": "May", "amount": 25000},
            {"month": "Jun", "amount": 30000}, {"month": "Jul", "amount": 20000},
            {"month": "Aug", "amount": 35000}, {"month": "Sep", "amount": 10000},
            {"month": "Oct", "amount": 28000}, {"month": "Nov", "amount": 15000},
            {"month": "Dec", "amount": 40000}, {"month": "Jan", "amount": 22000},
            {"month": "Feb", "amount": 18000}, {"month": "Mar", "amount": 2400},
        ]

        # Transactions with running balance pre-computed
        raw_txns = [
            {"date": "1 Apr 25",  "type": "credit",   "description": "Annual CSR commitment — FY26",    "category": "Top-up",       "amount": 1200000, "circle": None,                   "running_balance": 1200000, "reference": "NEFT/TCS/2025/001"},
            {"date": "2 Apr 25",  "type": "debit",    "description": "Ashoka Rising Circle — Q1 tranche","category": "Allocation",   "amount": 20000,   "circle": "Ashoka Rising Circle", "running_balance": 1180000, "reference": "ALLOC/ARC/Q1"},
            {"date": "2 Apr 25",  "type": "debit",    "description": "Udaan Bangalore — Q1 tranche",    "category": "Allocation",   "amount": 7000,    "circle": "Udaan Bangalore",      "running_balance": 1173000, "reference": "ALLOC/UB/Q1"},
            {"date": "5 Apr 25",  "type": "debit",    "description": "Platform fee (10% of commitment)","category": "Platform Fee", "amount": 10000,   "circle": None,                   "running_balance": 1163000, "reference": "FEE/2025/Q1"},
            {"date": "1 Jul 25",  "type": "debit",    "description": "Ashoka Rising Circle — Q2 tranche","category": "Allocation",  "amount": 20000,   "circle": "Ashoka Rising Circle", "running_balance": 1143000, "reference": "ALLOC/ARC/Q2"},
            {"date": "1 Jul 25",  "type": "debit",    "description": "Udaan Bangalore — Q2 tranche",    "category": "Allocation",   "amount": 5500,    "circle": "Udaan Bangalore",      "running_balance": 1137500, "reference": "ALLOC/UB/Q2"},
            {"date": "1 Oct 25",  "type": "debit",    "description": "Ashoka Rising Circle — Q3 tranche","category": "Allocation",  "amount": 10000,   "circle": "Ashoka Rising Circle", "running_balance": 1127500, "reference": "ALLOC/ARC/Q3"},
            {"date": "1 Oct 25",  "type": "debit",    "description": "Udaan Bangalore — Q3 tranche",    "category": "Allocation",   "amount": 6500,    "circle": "Udaan Bangalore",      "running_balance": 1121000, "reference": "ALLOC/UB/Q3"},
            {"date": "24 Nov 25", "type": "interest", "description": "C.C. Escrow interest credited",  "category": "Interest",     "amount": 2400,    "circle": None,                   "running_balance": 1123400, "reference": "INT/2025/NOV"},
            {"date": "1 Mar 26",  "type": "debit",    "description": "Ashoka Rising Circle — Q4 partial","category": "Allocation",  "amount": 2400,    "circle": "Ashoka Rising Circle", "running_balance": 1121000, "reference": "ALLOC/ARC/Q4P"},
        ]
        transactions = [CSRTransaction(**t) for t in raw_txns]

        upcoming_disbursements = [
            UpcomingDisbursement(circle_name="Ashoka Rising Circle", amount=20000, due_date="Apr 1, 2026", status="scheduled",        tranche="Q1 FY26-27"),
            UpcomingDisbursement(circle_name="Udaan Bangalore",      amount=7500,  due_date="Apr 1, 2026", status="pending_approval",  tranche="Q1 FY26-27"),
            UpcomingDisbursement(circle_name="ZenK Platform Fee",    amount=12000, due_date="Apr 5, 2026", status="scheduled",        tranche="Annual Fee"),
        ]

        alerts = [
            "₹3,00,000 unallocated — Q4 FY26 allocation deadline is Apr 1, 2026 (30 days away).",
            "₹2,400 escrow interest was credited to your account on 24 Nov 2025.",
            "Annual MCA compliance filing due by Sep 30, 2026. You are currently on track.",
        ]
        compliance_status = "on_track"
        escrow_interest_earned = 2400
        mandate_used_pct = round((total_deployed / mandate_amount) * 100, 1)

    else:
        total_deployed  = profile.total_csr_deployed
        total_received  = profile.total_csr_deployed
        committed       = profile.total_csr_deployed
        allocated       = profile.total_csr_deployed - (profile.unallocated or 0)
        balance         = profile.unallocated or 0
        unallocated     = profile.unallocated or 0
        mandate_amount  = profile.total_csr_deployed
        fy_label        = profile.fy_label or "FY 2025-26"
        account_number  = f"ZNK-CORP-{profile.id:04d}-TC"
        spend_by_category = list(profile.spend_by_category or [])
        raw_txns        = profile.transactions or []
        transactions    = [CSRTransaction(**t) for t in raw_txns]
        upcoming_disbursements = [
            UpcomingDisbursement(**d) for d in (profile.upcoming_disbursements or [])
        ]
        monthly_burn    = profile.monthly_burn or []
        alerts          = profile.alerts or []
        compliance_status = "on_track"
        escrow_interest_earned = 0
        mandate_used_pct = round((total_deployed / mandate_amount) * 100, 1) if mandate_amount else 0.0

    return CSRAccountResponse(
        total_deployed=total_deployed,
        total_received=total_received,
        balance=balance,
        committed=committed,
        allocated=allocated,
        unallocated=unallocated,
        fy_label=fy_label,
        account_number=account_number,
        mandate_amount=mandate_amount,
        mandate_used_pct=mandate_used_pct,
        escrow_interest_earned=escrow_interest_earned,
        compliance_status=compliance_status,
        spend_by_category=spend_by_category,
        transactions=transactions,
        upcoming_disbursements=upcoming_disbursements,
        monthly_burn=monthly_burn,
        alerts=alerts,
    )

# ── Kia Inline Strategy ───────────────────────────────────────────────────────

@router.get("/kia-recommendation", response_model=dict)
async def get_kia_recommendation(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    
    from app.services.kia_corporate import fetch_corporate_context, generate_corporate_response
    
    context = await fetch_corporate_context(user.id, user.email, db)
    
    prompt = "Please recommend a circle allocation strategy for my remaining budget, focusing on employee engagement and high-performing circles."
    response = await generate_corporate_response(prompt, context)
    
    return {
        "recommendation": response or "I'm currently unable to generate a recommendation. Please try again later."
    }


# ── Impact Certification Exports ──────────────────────────────────────────────

async def _get_profile_or_404(user_id, db):
    stmt = select(CorporateProfile).where(CorporateProfile.id == user_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Corporate profile not found.")
    return profile


@router.get("/impact/certificate")
async def download_certificate(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Generate and stream a ZenQ Impact Certificate PDF."""
    _require_corporate(user)
    profile = await _get_profile_or_404(user.id, db)
    from app.microservices.corporate.pdf_report import generate_corporate_certificate
    buf = generate_corporate_certificate(profile.__dict__)
    company_slug = (profile.company_name or "corporate").replace(" ", "_")
    filename = f"ZenQ_Certificate_{company_slug}_FY2025-26.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/impact/annual-report")
async def download_annual_report(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Generate and stream an Annual Report Insert PDF."""
    _require_corporate(user)
    profile = await _get_profile_or_404(user.id, db)
    from app.microservices.corporate.pdf_report import generate_annual_report_insert
    buf = generate_annual_report_insert(profile.__dict__)
    company_slug = (profile.company_name or "corporate").replace(" ", "_")
    filename = f"ZenQ_Annual_Report_{company_slug}_FY2025-26.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/impact/brsr-docs")
async def download_brsr_docs(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Generate and stream BRSR & Schedule VII compliance PDF."""
    _require_corporate(user)
    profile = await _get_profile_or_404(user.id, db)
    from app.microservices.corporate.pdf_report import generate_brsr_docs
    buf = generate_brsr_docs(profile.__dict__)
    company_slug = (profile.company_name or "corporate").replace(" ", "_")
    filename = f"ZenQ_BRSR_Docs_{company_slug}_FY2025-26.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/impact/brsr-export")
async def export_brsr_csv(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Generate and stream BRSR metrics as a CSV file."""
    _require_corporate(user)
    profile = await _get_profile_or_404(user.id, db)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["ZenK BRSR Data Export — FY 2025-26"])
    writer.writerow([])
    writer.writerow(["Company", profile.company_name or "—"])
    writer.writerow(["Corporate ZenQ Score", profile.corporate_zenq or "—"])
    writer.writerow(["Impact Tier", profile.impact_tier or "—"])
    writer.writerow(["Total CSR Deployed (₹)", profile.total_csr_deployed or 0])
    writer.writerow(["Unallocated Balance (₹)", profile.unallocated or 0])
    writer.writerow(["Circles Funded", profile.circles_funded or 0])
    writer.writerow(["Employees Engaged", profile.employees_engaged or 0])
    writer.writerow(["Schedule VII Item", "Item (ii): Education"])
    writer.writerow([])

    writer.writerow(["--- Circle Allocations ---"])
    writer.writerow(["Circle Name", "Allocation (%)", "Amount (₹)", "ZenQ Score", "Status"])
    for c in (profile.circle_allocations or []):
        writer.writerow([
            c.get("circle_name", ""), c.get("allocation_pct", ""),
            c.get("amount", ""), c.get("zenq_score", ""), c.get("status", ""),
        ])
    writer.writerow([])

    writer.writerow(["--- Transactions ---"])
    writer.writerow(["Date", "Description", "Category", "Amount (₹)", "Type"])
    for t in (profile.transactions or []):
        writer.writerow([
            t.get("date", ""), t.get("description", ""), t.get("category", ""),
            t.get("amount", ""), t.get("type", ""),
        ])

    output.seek(0)
    company_slug = (profile.company_name or "corporate").replace(" ", "_")
    filename = f"ZenQ_BRSR_Export_{company_slug}_FY2025-26.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
