"""Student dashboard microservice API."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_auth import get_current_user
from app.db.session import get_db
from app.models.enums import Persona
from app.models.signup import SignupRequest
from app.models.student_portal import StudentKiaMessage
from app.microservices.student.schemas import (
    StudentCircleJoinRequest,
    StudentKiaChatRequest,
    StudentKiaChatResponse,
    StudentKiaMessageOut,
    StudentMentoringPostRequest,
    StudentOverviewOut,
    StudentProfileOut,
)
from app.services.kia_student import (
    fetch_student_context,
    generate_student_priorities,
    generate_student_response,
)
from app.services.student_dashboard import (
    build_student_circle_view,
    build_student_overview,
    build_student_profile,
    build_student_progress,
)
from app.services.student_circle_enrollment import (
    list_circles_for_student,
    student_join_status,
    submit_student_circle_join,
)
from app.services.student_onboarding_v2 import (
    build_onboarding_timeline,
    list_open_circles_for_students,
    list_probe_messages,
    list_student_circle_interests,
    post_probe_message,
    submit_circle_interest,
)
from app.services.student_mentoring import (
    get_or_create_default_thread,
    list_messages,
    list_threads,
    post_mentor_reply,
    post_student_message,
)

router = APIRouter(prefix="/student", tags=["student-dashboard"])


def _require_student(user: SignupRequest) -> None:
    if user.persona != Persona.student:
        raise HTTPException(status_code=403, detail="Student persona required")


@router.get("/onboarding/timeline")
async def student_onboarding_timeline(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return await build_onboarding_timeline(db, user)


@router.get("/circle-interests")
async def student_circle_interests(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return await list_student_circle_interests(db, user)


@router.get("/circles/open")
async def student_open_circles(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return await list_open_circles_for_students(db)


@router.post("/circle-interest")
async def student_circle_interest(
    body: dict,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return await submit_circle_interest(
        db,
        user,
        circle_id=(body.get("circle_id") or "").strip(),
        help_comment=(body.get("help_comment") or "").strip(),
    )


@router.get("/circle-interest/{request_id}/probe-messages")
async def student_probe_messages(
    request_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return await list_probe_messages(db, request_id, user)


@router.post("/circle-interest/{request_id}/probe-messages")
async def student_post_probe(
    request_id: str,
    body: dict,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return await post_probe_message(
        db,
        request_id=request_id,
        sender=user,
        body=(body.get("body") or "").strip(),
        sender_role="student",
    )


@router.get("/profile", response_model=StudentProfileOut)
async def student_profile(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    data = await build_student_profile(db, user)
    return StudentProfileOut(**{k: data[k] for k in StudentProfileOut.model_fields})


@router.get("/overview", response_model=StudentOverviewOut)
async def student_overview(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    data = await build_student_overview(db, user)
    return StudentOverviewOut(
        signup_id=data["signup_id"],
        pseudonym=data["pseudonym"],
        avatar_key=data.get("avatar_key"),
        grade=data.get("grade"),
        school_label=data.get("school_label"),
        circle_name_masked=data.get("circle_name_masked"),
        school_linked=data.get("school_linked", False),
        kpis=data.get("kpis") or {},
        school_note=data.get("school_note"),
        milestones=data.get("milestones") or [],
    )


@router.get("/progress")
async def student_progress(
    quarter: str = "Q4",
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return await build_student_progress(db, user, quarter=quarter)


@router.get("/circle")
async def student_circle(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return await build_student_circle_view(db, user)


@router.get("/circle-join/status")
async def student_circle_join_status(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return await student_join_status(db, user)


@router.get("/circle-join/circles")
async def student_available_circles(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return await list_circles_for_student(db)


@router.post("/circle-join/request")
async def student_request_circle_join(
    body: StudentCircleJoinRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    try:
        return await submit_student_circle_join(db, user, circle_id=body.circle_id.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/kia-priorities")
async def student_kia_priorities(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    items = await generate_student_priorities(db, user)
    return {"items": items}


@router.get("/kia-chat/history", response_model=List[StudentKiaMessageOut])
async def student_kia_history(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    res = await db.execute(
        select(StudentKiaMessage)
        .where(StudentKiaMessage.student_signup_id == user.id)
        .order_by(StudentKiaMessage.created_at.asc())
    )
    return [
        StudentKiaMessageOut(
            id=m.id,
            role=m.role,
            text=m.text,
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in res.scalars().all()
    ]


@router.post("/kia-chat", response_model=StudentKiaChatResponse)
async def student_kia_chat(
    body: StudentKiaChatRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    user_msg = StudentKiaMessage(student_signup_id=user.id, role="user", text=body.message.strip())
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    ctx = await fetch_student_context(db, user)
    reply = await generate_student_response(body.message, ctx)
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kia is temporarily unavailable. Please try again shortly.",
        )

    kia_msg = StudentKiaMessage(student_signup_id=user.id, role="kia", text=reply)
    db.add(kia_msg)
    await db.commit()
    await db.refresh(kia_msg)

    return StudentKiaChatResponse(
        reply=reply,
        user_message_id=user_msg.id,
        kia_message_id=kia_msg.id,
    )


@router.get("/mentoring/threads")
async def student_mentoring_threads(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return {"threads": await list_threads(db, user)}


@router.get("/mentoring/threads/{thread_id}/messages")
async def student_mentoring_messages(
    thread_id: str,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    return {"messages": await list_messages(db, user, thread_id)}


@router.post("/mentoring/threads/{thread_id}/messages")
async def student_mentoring_send(
    thread_id: str,
    body: StudentMentoringPostRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    msg = await post_student_message(db, user, thread_id, body.body)
    return msg


@router.post("/mentoring/threads/{thread_id}/reply")
async def mentoring_reply(
    thread_id: str,
    body: StudentMentoringPostRequest,
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mentor or circle member text reply (no video/voice in Phase 2)."""
    return await post_mentor_reply(db, user, thread_id, body.body)


@router.post("/mentoring/ensure-default")
async def ensure_default_thread(
    user: SignupRequest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(user)
    thread = await get_or_create_default_thread(db, user)
    await db.commit()
    return {"thread_id": thread.id, "title": thread.title}
