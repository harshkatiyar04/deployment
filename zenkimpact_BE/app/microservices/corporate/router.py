"""Corporate CSR Dashboard — FastAPI Router."""
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

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
        raise HTTPException(status_code=404, detail="Corporate profile not found.")
        
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
        raise HTTPException(status_code=404, detail="Corporate profile not found.")

    trend_data = [ZenQTrendPoint(**p) for p in (profile.zenq_trend or [])]
    weighted_score = profile.corporate_zenq or 0.0

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
        raise HTTPException(status_code=404, detail="Corporate profile not found.")

    circles = [CircleAllocation(**c) for c in (profile.circle_allocations or [])]
    total_csr = profile.total_csr_deployed or 0
    unallocated = profile.unallocated or 0

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
        raise HTTPException(status_code=404, detail="Corporate profile not found.")

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

    if not profile:
        raise HTTPException(status_code=404, detail="Corporate profile not found.")

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
        monthly_hours=profile.monthly_hours or [],
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

    if not profile:
        raise HTTPException(status_code=404, detail="Corporate profile not found.")

    total_deployed  = profile.total_csr_deployed or 0
    total_received  = profile.total_csr_deployed or 0
    committed       = profile.total_csr_deployed or 0
    allocated       = (profile.total_csr_deployed or 0) - (profile.unallocated or 0)
    balance         = profile.unallocated or 0
    unallocated     = profile.unallocated or 0
    mandate_amount  = profile.total_csr_deployed or 0
    fy_label        = profile.fy_label or "FY 2025-26"
    account_number  = f"ZNK-CORP-{str(profile.id).split('-')[0].upper()}-TC"
    
    spend_by_category = list(profile.spend_by_category or [])
    
    raw_txns        = profile.transactions or []
    transactions    = [CSRTransaction(**t) for t in raw_txns]
    
    raw_upcoming = getattr(profile, 'upcoming_disbursements', []) or []
    upcoming_disbursements = [UpcomingDisbursement(**d) for d in raw_upcoming]
    
    monthly_burn    = getattr(profile, 'monthly_burn', []) or []
    alerts          = getattr(profile, 'alerts', []) or []
    
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

@router.post("/csr-account/disbursements", response_model=CSRAccountResponse)
async def add_disbursement(
    payload: UpcomingDisbursement,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Corporate profile not found")
        
    disbursements = getattr(profile, "upcoming_disbursements", []) or []
    disbursements.append(payload.model_dump())
    profile.upcoming_disbursements = disbursements
    
    flag_modified(profile, "upcoming_disbursements")
    await db.commit()
    
    return await get_csr_account(db, user)

@router.delete("/csr-account/disbursements/{index}", response_model=CSRAccountResponse)
async def delete_disbursement(
    index: int,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Corporate profile not found")
        
    disbursements = getattr(profile, "upcoming_disbursements", []) or []
    if 0 <= index < len(disbursements):
        disbursements.pop(index)
        profile.upcoming_disbursements = disbursements
        flag_modified(profile, "upcoming_disbursements")
        await db.commit()
        
    return await get_csr_account(db, user)

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

from datetime import datetime

@router.get("/kia-strategy-brief", response_model=dict)
async def get_kia_strategy_brief(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
    force_refresh: bool = False
):
    _require_corporate(user)
    
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    # Check if we have a recent brief
    now_str = datetime.utcnow().isoformat()
    brief = profile.strategy_brief or {}
    
    if not force_refresh and brief and brief.get("priorities"):
        return brief
        
    # Generate new brief
    from app.services.kia_corporate import fetch_corporate_context, generate_strategy_brief
    context = await fetch_corporate_context(user.id, user.email, db)
    priorities = await generate_strategy_brief(context)
    
    if priorities:
        new_brief = {
            "generated_at": now_str,
            "priorities": priorities
        }
        profile.strategy_brief = new_brief
        flag_modified(profile, "strategy_brief")
        await db.commit()
        return new_brief
        
    return {
        "generated_at": now_str,
        "priorities": [
            {
                "title": "Strategy engine offline",
                "body": "Kia is currently unable to generate your strategy brief. Please try again.",
                "urgency": "medium"
            }
        ]
    }

@router.get("/peer-benchmark", response_model=list)
async def get_peer_benchmarks(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    
    # In a real app, query all CorporateProfiles, sort by zenq.
    # For MVP, mock realistic data and insert the user in the middle.
    
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    user_zenq = profile.corporate_zenq if profile else 78.4
    user_name = profile.company_name if profile else "Your Company"
    
    benchmarks = [
        {"rank": 1, "label": "Corporate A", "sector": "Technology sector", "zenq": 88.2, "is_you": False},
        {"rank": 2, "label": "Corporate B", "sector": "FMCG sector", "zenq": 83.1, "is_you": False},
        {"rank": 3, "label": user_name, "sector": "You", "zenq": user_zenq, "is_you": True},
        {"rank": 4, "label": "Corporate C", "sector": "Banking", "zenq": 72.0, "is_you": False},
        {"rank": 5, "label": "Corporate D", "sector": "Pharma", "zenq": 65.3, "is_you": False},
    ]
    
    return benchmarks

@router.get("/corporate-goals", response_model=list)
async def get_corporate_goals(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_corporate(user)
    stmt = select(CorporateProfile).where(CorporateProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if profile and profile.corporate_goals:
        return profile.corporate_goals
        
    return []


# ── Kia Chat & Scenario Planner (Live LLM) ───────────────────────────────────

from pydantic import BaseModel as _PydanticBase

class _KiaChatRequest(_PydanticBase):
    message: str
    is_scenario: bool = False

@router.post("/kia-chat")
async def kia_chat(
    body: _KiaChatRequest,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    """Send a message to Kia (strategy chat or scenario planner)."""
    _require_corporate(user)

    from app.services.kia_corporate import fetch_corporate_context, generate_corporate_response

    context = await fetch_corporate_context(user.id, user.email, db)

    if body.is_scenario:
        prompt = (
            "The corporate user is asking you to MODEL A SCENARIO. "
            "Analyse the hypothetical situation they describe, estimate the "
            "likely change to their Corporate ZenQ score, and provide concrete "
            "recommendations. Use numbers from the Corporate Context. "
            "Be concise but data-rich.\n\n"
            f"User's scenario: \"{body.message}\""
        )
    else:
        prompt = body.message

    reply = await generate_corporate_response(prompt, context)

    if not reply:
        raise HTTPException(
            status_code=502,
            detail="Kia is temporarily unable to respond. Please try again.",
        )

    return {"response": reply}


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
