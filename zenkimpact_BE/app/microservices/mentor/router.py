"""Mentor Dashboard — FastAPI Router."""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.jwt_auth import get_current_user
from app.models.signup import SignupRequest
from app.models.enums import Persona
from app.models.mentor import MentorProfile, MentorSession, MentorUpliftAction, MentorKiaMessage
from app.microservices.mentor.schemas import (
    MentorProfileResponse,
    MentorSessionCreate, MentorSessionResponse,
    InspireIndexResponse, InspireBreakdownItem,
    UpliftActionCreate, UpliftActionResponse, AdminUpliftActionResponse,
    MentorKiaChatRequest, MentorKiaChatResponse, MentorKiaMessageResponse,
    MentorStatementResponse,
)
from app.services.kia_mentor import (
    fetch_mentor_context,
    generate_mentor_response,
    generate_mentor_inspire_insight,
)

router = APIRouter(prefix="/mentor", tags=["Mentor Dashboard"])


# ── Guard ─────────────────────────────────────────────────────────────────────

def _require_mentor(user: SignupRequest) -> SignupRequest:
    if user.persona != Persona.mentor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mentor dashboard is restricted to mentor accounts.",
        )
    return user


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _compute_inspire_pts(duration_hrs: float, engagement_level: str, inspiration_shared: str | None) -> float:
    """Calculate InspireIndex points earned for a single session."""
    pts = 0.2  # base per session
    if engagement_level.lower() in ("highly engaged", "highly engaged — asked great questions"):
        pts += 0.4
    if inspiration_shared and len(inspiration_shared.strip()) > 30:
        pts += 0.3
    return round(pts, 2)


def _compute_zenq_impact(duration_hrs: float, engagement_level: str) -> float:
    """Estimate ZenQ impact of a session."""
    base = duration_hrs * 0.08
    if "highly" in engagement_level.lower():
        base *= 1.5
    return round(base, 2)


def _rebuild_kpis(profile: MentorProfile, sessions: list, uplifts: list) -> None:
    """Recompute all aggregate KPIs from raw session/uplift data and patch the profile."""
    verified_uplifts = [u for u in uplifts if getattr(u, 'verified', False)]
    
    profile.sessions_this_fy = len(sessions)
    profile.hours_mentored = round(sum(s.duration_hrs for s in sessions), 1)
    profile.community_uplift_count = len(verified_uplifts)

    # InspireIndex: sum of all session inspire_pts + verified uplift actions
    raw_inspire = sum(s.inspire_pts for s in sessions)
    raw_inspire += sum(u.impact_score for u in verified_uplifts)
    profile.inspire_index = min(round(raw_inspire, 1), 100.0)

    # ZenQ contribution
    profile.zenq_contribution = round(sum(s.zenq_impact for s in sessions), 1)

    # Breakdown (5 axes)
    session_consistency = round(min(len(sessions) * 0.3, 40.0), 1)
    student_engagement = round(
        sum(0.4 if "highly" in s.engagement_level.lower() else 0.2 for s in sessions), 1
    )
    topic_diversity = round(len({s.topic_area for s in sessions}) * 0.3, 1)
    community_uplift_pts = round(sum(u.impact_score for u in verified_uplifts), 1)
    circle_feedback = 0.4  # static for now — requires circle leader feedback integration

    profile.inspire_breakdown = {
        "session_consistency": session_consistency,
        "student_engagement": round(min(student_engagement, 30.0), 1),
        "topic_diversity": round(min(topic_diversity, 15.0), 1),
        "community_uplift": round(min(community_uplift_pts, 10.0), 1),
        "circle_feedback_score": circle_feedback,
    }

    profile.updated_at = datetime.utcnow()


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=MentorProfileResponse)
async def get_mentor_profile(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_mentor(user)

    stmt = select(MentorProfile).where(MentorProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentor profile not found. Please contact your ZenK administrator.",
        )

    return MentorProfileResponse(
        id=profile.id,
        mentor_id=profile.mentor_id,
        full_name=user.full_name,
        specialty=profile.specialty,
        city=profile.city,
        tier=profile.tier,
        tier_label=profile.tier_label,
        assigned_circles=profile.assigned_circles or [],
        badges=profile.badges or [],
        sessions_this_fy=profile.sessions_this_fy,
        hours_mentored=profile.hours_mentored,
        inspire_index=profile.inspire_index,
        inspire_index_percentile=profile.inspire_index_percentile,
        inspire_index_delta=profile.inspire_index_delta,
        zenq_contribution=profile.zenq_contribution,
        community_uplift_count=profile.community_uplift_count,
        inspire_breakdown=profile.inspire_breakdown or {},
        circle_id=str(profile.circle_id) if getattr(profile, "circle_id", None) else None,
    )



# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=List[MentorSessionResponse])
async def list_mentor_sessions(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_mentor(user)

    stmt = (
        select(MentorSession)
        .where(MentorSession.mentor_id == user.id)
        .order_by(MentorSession.session_date.desc())
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    return [
        MentorSessionResponse(
            id=s.id,
            student_circle=s.student_circle,
            session_date=s.session_date,
            topic_area=s.topic_area,
            duration_hrs=s.duration_hrs,
            mode=s.mode,
            engagement_level=s.engagement_level,
            session_notes=s.session_notes,
            inspiration_shared=s.inspiration_shared,
            zenq_impact=s.zenq_impact,
            inspire_pts=s.inspire_pts,
            gross_amount=s.duration_hrs * 500,
            commission=(s.duration_hrs * 500) * 0.05,
            net_amount=(s.duration_hrs * 500) * 0.95,
            status="Processed",
            created_at=s.created_at.isoformat(),
        )
        for s in sessions
    ]


@router.post("/sessions", response_model=MentorSessionResponse, status_code=status.HTTP_201_CREATED)
async def log_mentor_session(
    body: MentorSessionCreate,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_mentor(user)

    # Fetch profile to update KPIs
    stmt = select(MentorProfile).where(MentorProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Mentor profile not found.")

    inspire_pts = _compute_inspire_pts(body.duration_hrs, body.engagement_level, body.inspiration_shared)
    zenq_impact = _compute_zenq_impact(body.duration_hrs, body.engagement_level)

    session = MentorSession(
        id=str(uuid.uuid4()),
        mentor_id=user.id,
        student_circle=body.student_circle,
        session_date=body.session_date,
        topic_area=body.topic_area,
        duration_hrs=body.duration_hrs,
        mode=body.mode,
        engagement_level=body.engagement_level,
        session_notes=body.session_notes,
        inspiration_shared=body.inspiration_shared,
        zenq_impact=zenq_impact,
        inspire_pts=inspire_pts,
    )
    db.add(session)

    # Rebuild KPIs
    all_sessions_stmt = select(MentorSession).where(MentorSession.mentor_id == user.id)
    all_sessions_result = await db.execute(all_sessions_stmt)
    all_sessions = list(all_sessions_result.scalars().all()) + [session]

    uplifts_stmt = select(MentorUpliftAction).where(MentorUpliftAction.mentor_id == user.id)
    uplifts_result = await db.execute(uplifts_stmt)
    uplifts = list(uplifts_result.scalars().all())

    _rebuild_kpis(profile, all_sessions, uplifts)

    await db.commit()
    await db.refresh(session)

    return MentorSessionResponse(
        id=session.id,
        student_circle=session.student_circle,
        session_date=session.session_date,
        topic_area=session.topic_area,
        duration_hrs=session.duration_hrs,
        mode=session.mode,
        engagement_level=session.engagement_level,
        session_notes=session.session_notes,
        inspiration_shared=session.inspiration_shared,
        zenq_impact=session.zenq_impact,
        inspire_pts=session.inspire_pts,
        gross_amount=session.duration_hrs * 500,
        commission=(session.duration_hrs * 500) * 0.05,
        net_amount=(session.duration_hrs * 500) * 0.95,
        status="Pending",
        created_at=session.created_at.isoformat(),
    )


# ── InspireIndex ──────────────────────────────────────────────────────────────

SCORING_RULES = [
    {"label": "Per mentoring session logged", "detail": "With session notes of 50+ words", "pts": "+0.2 pts / session"},
    {"label": "Highly engaged session rating", "detail": "When student engagement is logged as high", "pts": "+0.4 pts / session"},
    {"label": "Inspiration story shared", "detail": "Real-world stories of overcoming adversity", "pts": "+0.3 pts / session"},
    {"label": "Circle member positive feedback", "detail": "Rated by the Sponsor Leader after each session", "pts": "+0.5 pts / feedback"},
    {"label": "Student sets and achieves a goal you suggested", "detail": "Tracked via ZenK impact and school reports", "pts": "+1.0 pt / milestone"},
    {"label": "Community uplift action completed", "detail": "Guest talks, career events, resource sharing", "pts": "+0.8 pts / action"},
]

INSPIRE_AXIS_META = {
    "session_consistency": {"label": "Session consistency", "max_score": 40.0, "pts_label": "pts"},
    "student_engagement": {"label": "Student engagement", "max_score": 30.0, "pts_label": "pts"},
    "topic_diversity": {"label": "Topic diversity", "max_score": 15.0, "pts_label": "pts"},
    "community_uplift": {"label": "Community uplift", "max_score": 10.0, "pts_label": "pts"},
    "circle_feedback_score": {"label": "Circle feedback score", "max_score": 5.0, "pts_label": "pts"},
}


@router.get("/inspire-index", response_model=InspireIndexResponse)
async def get_inspire_index(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_mentor(user)

    stmt = select(MentorProfile).where(MentorProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Mentor profile not found.")

    breakdown_data = profile.inspire_breakdown or {}
    breakdown_items = []
    for key, meta in INSPIRE_AXIS_META.items():
        score = breakdown_data.get(key, 0.0)
        breakdown_items.append(InspireBreakdownItem(
            label=meta["label"],
            score=score,
            max_score=meta["max_score"],
            pts_label=f"+{score} {meta['pts_label']}",
        ))

    # Generate fresh Kia insight (or return cached)
    kia_insight = profile.kia_insight
    if not kia_insight:
        mentor_context = await fetch_mentor_context(user.id, db)
        kia_insight = await generate_mentor_inspire_insight(mentor_context)
        if kia_insight:
            profile.kia_insight = kia_insight
            await db.commit()

    return InspireIndexResponse(
        total=profile.inspire_index,
        percentile=profile.inspire_index_percentile,
        delta=profile.inspire_index_delta,
        breakdown=breakdown_items,
        scoring_rules=SCORING_RULES,
        kia_insight=kia_insight,
    )


# ── Uplift Actions ────────────────────────────────────────────────────────────

ACTION_TYPE_SCORES = {
    "guest_talk": 0.8,
    "career_event": 0.8,
    "resource_sharing": 0.5,
    "other": 0.3,
}


@router.get("/uplift-actions", response_model=List[UpliftActionResponse])
async def list_uplift_actions(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_mentor(user)

    stmt = (
        select(MentorUpliftAction)
        .where(MentorUpliftAction.mentor_id == user.id)
        .order_by(MentorUpliftAction.event_date.desc())
    )
    result = await db.execute(stmt)
    actions = result.scalars().all()

    return [
        UpliftActionResponse(
            id=a.id,
            action_type=a.action_type,
            title=a.title,
            description=a.description,
            event_date=a.event_date,
            impact_score=a.impact_score,
            verified=a.verified,
            created_at=a.created_at.isoformat(),
        )
        for a in actions
    ]


@router.post("/uplift-actions", response_model=UpliftActionResponse, status_code=status.HTTP_201_CREATED)
async def log_uplift_action(
    body: UpliftActionCreate,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_mentor(user)

    stmt = select(MentorProfile).where(MentorProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Mentor profile not found.")

    impact_score = ACTION_TYPE_SCORES.get(body.action_type, 0.3)

    action = MentorUpliftAction(
        id=str(uuid.uuid4()),
        mentor_id=user.id,
        action_type=body.action_type,
        title=body.title,
        description=body.description,
        event_date=body.event_date,
        impact_score=impact_score,
        verified=False,
    )
    db.add(action)

    # Rebuild KPIs
    sessions_stmt = select(MentorSession).where(MentorSession.mentor_id == user.id)
    sessions_result = await db.execute(sessions_stmt)
    sessions = list(sessions_result.scalars().all())

    uplifts_stmt = select(MentorUpliftAction).where(MentorUpliftAction.mentor_id == user.id)
    uplifts_result = await db.execute(uplifts_stmt)
    uplifts = list(uplifts_result.scalars().all()) + [action]

    _rebuild_kpis(profile, sessions, uplifts)

    await db.commit()
    await db.refresh(action)

    return UpliftActionResponse(
        id=action.id,
        action_type=action.action_type,
        title=action.title,
        description=action.description,
        event_date=action.event_date,
        impact_score=action.impact_score,
        verified=action.verified,
        created_at=action.created_at.isoformat(),
    )
@router.get("/admin/uplift-actions", response_model=List[AdminUpliftActionResponse])
async def admin_list_uplift_actions(db: AsyncSession = Depends(get_db)):
    """List all uplift actions (pending and verified) for admin review."""
    # Note: In a real app, this should have admin auth checks
    stmt = (
        select(MentorUpliftAction, MentorProfile, SignupRequest)
        .join(MentorProfile, MentorUpliftAction.mentor_id == MentorProfile.id)
        .join(SignupRequest, MentorProfile.id == SignupRequest.id)
        .order_by(MentorUpliftAction.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        AdminUpliftActionResponse(
            id=action.id,
            action_type=action.action_type,
            title=action.title,
            description=action.description,
            event_date=action.event_date,
            impact_score=action.impact_score,
            verified=action.verified,
            created_at=action.created_at.isoformat(),
            mentor_id=profile.id,
            mentor_name=signup.full_name,
            mentor_specialty=profile.specialty,
        )
        for action, profile, signup in rows
    ]

@router.patch("/admin/uplift-actions/{action_id}/verify", response_model=AdminUpliftActionResponse)
async def admin_verify_uplift_action(action_id: str, db: AsyncSession = Depends(get_db)):
    """Verify an uplift action and rebuild mentor KPIs."""
    stmt = (
        select(MentorUpliftAction, MentorProfile, SignupRequest)
        .join(MentorProfile, MentorUpliftAction.mentor_id == MentorProfile.id)
        .join(SignupRequest, MentorProfile.id == SignupRequest.id)
        .where(MentorUpliftAction.id == action_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Uplift action not found.")
        
    action, profile, signup = row
    
    if action.verified:
        raise HTTPException(status_code=400, detail="Action is already verified.")
        
    action.verified = True
    
    # Rebuild KPIs for this mentor
    sessions_stmt = select(MentorSession).where(MentorSession.mentor_id == profile.id)
    sessions_result = await db.execute(sessions_stmt)
    sessions = list(sessions_result.scalars().all())

    uplifts_stmt = select(MentorUpliftAction).where(MentorUpliftAction.mentor_id == profile.id)
    uplifts_result = await db.execute(uplifts_stmt)
    uplifts = list(uplifts_result.scalars().all())

    _rebuild_kpis(profile, sessions, uplifts)
    
    await db.commit()
    await db.refresh(action)
    
    return AdminUpliftActionResponse(
        id=action.id,
        action_type=action.action_type,
        title=action.title,
        description=action.description,
        event_date=action.event_date,
        impact_score=action.impact_score,
        verified=action.verified,
        created_at=action.created_at.isoformat(),
        mentor_id=profile.id,
        mentor_name=signup.full_name,
        mentor_specialty=profile.specialty,
    )

@router.delete("/admin/uplift-actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_reject_uplift_action(action_id: str, db: AsyncSession = Depends(get_db)):
    """Reject (delete) an uplift action."""
    stmt = select(MentorUpliftAction).where(MentorUpliftAction.id == action_id)
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()
    
    if not action:
        raise HTTPException(status_code=404, detail="Uplift action not found.")
        
    mentor_id = action.mentor_id
    was_verified = action.verified
    
    await db.delete(action)
    
    # Rebuild KPIs if it was verified
    if was_verified:
        profile_stmt = select(MentorProfile).where(MentorProfile.id == mentor_id)
        profile_result = await db.execute(profile_stmt)
        profile = profile_result.scalar_one_or_none()
        
        if profile:
            sessions_stmt = select(MentorSession).where(MentorSession.mentor_id == profile.id)
            sessions_result = await db.execute(sessions_stmt)
            sessions = list(sessions_result.scalars().all())

            uplifts_stmt = select(MentorUpliftAction).where(MentorUpliftAction.mentor_id == profile.id)
            uplifts_result = await db.execute(uplifts_stmt)
            uplifts = list(uplifts_result.scalars().all())

            _rebuild_kpis(profile, sessions, uplifts)
            
    await db.commit()
    return None

@router.get("/kia-chat/history", response_model=List[MentorKiaMessageResponse])
async def get_mentor_kia_chat_history(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_mentor(user)

    stmt = select(MentorKiaMessage).where(MentorKiaMessage.mentor_id == user.id).order_by(MentorKiaMessage.created_at.asc())
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [
        MentorKiaMessageResponse(
            id=m.id,
            mentor_id=m.mentor_id,
            role=m.role,
            text=m.text,
            created_at=m.created_at.isoformat()
        )
        for m in messages
    ]


@router.post("/kia-chat", response_model=MentorKiaChatResponse)
async def mentor_kia_chat(
    body: MentorKiaChatRequest,
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_mentor(user)

    # Save user message
    user_msg = MentorKiaMessage(mentor_id=user.id, role="user", text=body.message)
    db.add(user_msg)
    await db.commit()

    mentor_context = await fetch_mentor_context(user.id, db)
    reply = await generate_mentor_response(body.message, mentor_context)

    if not reply:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kia AI is temporarily unavailable. Please try again shortly.",
        )

    # Save Kia response
    kia_msg = MentorKiaMessage(mentor_id=user.id, role="kia", text=reply)
    db.add(kia_msg)
    await db.commit()

    return MentorKiaChatResponse(reply=reply)


# ── Statement ─────────────────────────────────────────────────────────────────

@router.get("/statement", response_model=MentorStatementResponse)
async def get_mentor_statement(
    db: AsyncSession = Depends(get_db),
    user: SignupRequest = Depends(get_current_user),
):
    _require_mentor(user)

    stmt = select(MentorProfile).where(MentorProfile.id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Mentor profile not found.")

    sessions_stmt = (
        select(MentorSession)
        .where(MentorSession.mentor_id == user.id)
        .order_by(MentorSession.session_date.desc())
    )
    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    uplifts_stmt = (
        select(MentorUpliftAction)
        .where(MentorUpliftAction.mentor_id == user.id)
        .order_by(MentorUpliftAction.event_date.desc())
    )
    uplifts_result = await db.execute(uplifts_stmt)
    uplifts = uplifts_result.scalars().all()

    return MentorStatementResponse(
        mentor_id=profile.mentor_id,
        full_name=user.full_name,
        specialty=profile.specialty,
        fy_label="FY 2025-26",
        total_sessions=profile.sessions_this_fy,
        total_hours=profile.hours_mentored,
        inspire_index=profile.inspire_index,
        zenq_contribution=profile.zenq_contribution,
        community_uplift_count=profile.community_uplift_count,
        sessions=[
            MentorSessionResponse(
                id=s.id,
                student_circle=s.student_circle,
                session_date=s.session_date,
                topic_area=s.topic_area,
                duration_hrs=s.duration_hrs,
                mode=s.mode,
                engagement_level=s.engagement_level,
                session_notes=s.session_notes,
                inspiration_shared=s.inspiration_shared,
                zenq_impact=s.zenq_impact,
                inspire_pts=s.inspire_pts,
                gross_amount=s.duration_hrs * 500,
                commission=(s.duration_hrs * 500) * 0.05,
                net_amount=(s.duration_hrs * 500) * 0.95,
                status="Processed",
                created_at=s.created_at.isoformat(),
            )
            for s in sessions
        ],
        uplift_actions=[
            UpliftActionResponse(
                id=a.id,
                action_type=a.action_type,
                title=a.title,
                description=a.description,
                event_date=a.event_date,
                impact_score=a.impact_score,
                verified=a.verified,
                created_at=a.created_at.isoformat(),
            )
            for a in uplifts
        ],
    )
