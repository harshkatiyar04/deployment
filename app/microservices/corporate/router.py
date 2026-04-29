"""Corporate CSR Dashboard — FastAPI Router."""
from fastapi import APIRouter, Depends, HTTPException, status
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
    CSRAccountResponse, CSRTransaction,
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
        if "corporate2" in user.email.lower() or "hcl" in user.email.lower():
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

    if not profile:
        total_enrolled = 12
        active_this_month = 9
        circles_participating = 2
        avg_hours_per_employee = 6.5
        metrics = [
            EngagementMetric(label="Total Enrolled", value="12", delta="+3 this FY", trend="up"),
            EngagementMetric(label="Active This Month", value="9", delta="+2 vs last month", trend="up"),
            EngagementMetric(label="Avg Hours/Employee", value="6.5h", delta="-0.5h vs last month", trend="down"),
            EngagementMetric(label="Volunteer Hours Total", value="78h", delta="+12h this month", trend="up"),
        ]
        top_contributors = [
            TopContributor(name="Priya Sharma", initials="PS", department="Engineering", hours=14, impact_score=92),
            TopContributor(name="Arjun Mehta", initials="AM", department="HR", hours=12, impact_score=88),
            TopContributor(name="Divya Nair", initials="DN", department="Finance", hours=11, impact_score=84),
            TopContributor(name="Rahul Joshi", initials="RJ", department="Product", hours=9, impact_score=81),
            TopContributor(name="Sneha Kapoor", initials="SK", department="Sales", hours=8, impact_score=79),
        ]
        monthly_hours = [
            {"month": "Apr", "hours": 32}, {"month": "May", "hours": 38}, {"month": "Jun", "hours": 41},
            {"month": "Jul", "hours": 44}, {"month": "Aug", "hours": 48}, {"month": "Sep", "hours": 52},
            {"month": "Oct", "hours": 58}, {"month": "Nov", "hours": 62}, {"month": "Dec", "hours": 65},
            {"month": "Jan", "hours": 70}, {"month": "Feb", "hours": 74}, {"month": "Mar", "hours": 78},
        ]
    else:
        total_enrolled = profile.employees_engaged
        active_this_month = 9
        circles_participating = profile.circles_funded
        avg_hours_per_employee = 6.5
        metrics = [EngagementMetric(**m) for m in (profile.engagement_metrics or [])]
        top_contributors = [TopContributor(**c) for c in (profile.top_contributors or [])]
        monthly_hours = [
            {"month": "Apr", "hours": 32}, {"month": "May", "hours": 38}, {"month": "Jun", "hours": 41},
            {"month": "Jul", "hours": 44}, {"month": "Aug", "hours": 48}, {"month": "Sep", "hours": 52},
            {"month": "Oct", "hours": 58}, {"month": "Nov", "hours": 62}, {"month": "Dec", "hours": 65},
            {"month": "Jan", "hours": 70}, {"month": "Feb", "hours": 74}, {"month": "Mar", "hours": 78},
        ]

    return EmployeeEngagementResponse(
        total_enrolled=total_enrolled,
        active_this_month=active_this_month,
        circles_participating=circles_participating,
        avg_hours_per_employee=avg_hours_per_employee,
        metrics=metrics,
        top_contributors=top_contributors,
        monthly_hours=monthly_hours,
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

    if not profile:
        total_deployed = 100000
        total_received = 100000
        balance = 20000
        fy_label = "FY 2025-26"
        spend_by_category = [
            {"category": "Student Circles", "amount": 80000, "color": "#00D4BE"},
            {"category": "Platform Fee", "amount": 10000, "color": "#F6C343"},
            {"category": "Unallocated", "amount": 20000, "color": "#4e4635"},
        ]
        transactions = [
            CSRTransaction(date="Mar 20, 2026", description="Ashoka Rising Circle — Q4 Tranche", category="Circle Fund", amount=15000, type="debit", circle="Ashoka Rising Circle"),
            CSRTransaction(date="Mar 10, 2026", description="Udaan Bangalore — Q4 Tranche", category="Circle Fund", amount=5000, type="debit", circle="Udaan Bangalore"),
            CSRTransaction(date="Feb 28, 2026", description="CSR Disbursement", category="Inflow", amount=100000, type="credit"),
            CSRTransaction(date="Jan 15, 2026", description="Platform Service Fee Q3", category="Platform Fee", amount=2500, type="debit"),
            CSRTransaction(date="Dec 20, 2025", description="Ashoka Rising Circle — Q3 Tranche", category="Circle Fund", amount=15000, type="debit", circle="Ashoka Rising Circle"),
            CSRTransaction(date="Dec 10, 2025", description="Udaan Bangalore — Q3 Tranche", category="Circle Fund", amount=5000, type="debit", circle="Udaan Bangalore"),
            CSRTransaction(date="Nov 5, 2025", description="Ashoka Rising Circle — Q2 Tranche", category="Circle Fund", amount=15000, type="debit", circle="Ashoka Rising Circle"),
            CSRTransaction(date="Oct 1, 2025", description="Platform Service Fee Q2", category="Platform Fee", amount=2500, type="debit"),
        ]
    else:
        total_deployed = profile.total_csr_deployed
        total_received = profile.total_csr_deployed
        balance = profile.unallocated
        fy_label = profile.fy_label
        spend_by_category = list(profile.spend_by_category or [])
        transactions = [CSRTransaction(**t) for t in (profile.transactions or [])]

    return CSRAccountResponse(
        total_deployed=total_deployed,
        total_received=total_received,
        balance=balance,
        fy_label=fy_label,
        spend_by_category=spend_by_category,
        transactions=transactions,
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
