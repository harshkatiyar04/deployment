"""Text-only mentoring threads between students and circle mentors/members."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember
from app.models.enums import Persona
from app.models.mentor import MentorProfile
from app.models.signup import SignupRequest
from app.models.student_portal import StudentMentoringMessage, StudentMentoringThread
from app.services.student_dashboard import resolve_student_circle_id, resolve_school_student


async def _require_student(user: SignupRequest) -> None:
    if user.persona != Persona.student:
        raise HTTPException(status_code=403, detail="Student account required")


async def get_or_create_default_thread(
    db: AsyncSession,
    student: SignupRequest,
) -> StudentMentoringThread:
    school_student = await resolve_school_student(db, student)
    circle_id = await resolve_student_circle_id(db, student, school_student)

    res = await db.execute(
        select(StudentMentoringThread)
        .where(StudentMentoringThread.student_signup_id == student.id)
        .order_by(StudentMentoringThread.updated_at.desc())
        .limit(1)
    )
    thread = res.scalar_one_or_none()
    if thread:
        return thread

    now = datetime.now(timezone.utc)
    thread = StudentMentoringThread(
        student_signup_id=student.id,
        circle_id=circle_id,
        title="Circle mentoring",
        status="open",
        created_at=now,
        updated_at=now,
    )
    db.add(thread)
    await db.flush()
    return thread


def _sender_label(role: str) -> str:
    return {
        "student": "You",
        "mentor": "Circle mentor",
        "member": "Circle supporter",
        "leader": "Circle leader",
    }.get(role, "Supporter")


async def list_threads(db: AsyncSession, student: SignupRequest) -> list[dict[str, Any]]:
    await _require_student(student)
    thread = await get_or_create_default_thread(db, student)
    await db.commit()

    msg_res = await db.execute(
        select(StudentMentoringMessage)
        .where(StudentMentoringMessage.thread_id == thread.id)
        .order_by(StudentMentoringMessage.created_at.desc())
        .limit(1)
    )
    last = msg_res.scalar_one_or_none()

    return [
        {
            "id": thread.id,
            "title": thread.title,
            "status": thread.status,
            "mode": "text",
            "last_message_preview": (last.body[:120] if last else None),
            "last_message_at": last.created_at.isoformat() if last and last.created_at else None,
            "unread_hint": False,
        }
    ]


async def list_messages(db: AsyncSession, student: SignupRequest, thread_id: str) -> list[dict]:
    await _require_student(student)
    thread_res = await db.execute(
        select(StudentMentoringThread).where(
            StudentMentoringThread.id == thread_id,
            StudentMentoringThread.student_signup_id == student.id,
        )
    )
    thread = thread_res.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    res = await db.execute(
        select(StudentMentoringMessage)
        .where(StudentMentoringMessage.thread_id == thread_id)
        .order_by(StudentMentoringMessage.created_at.asc())
    )
    return [
        {
            "id": m.id,
            "sender_label": _sender_label(m.sender_role),
            "sender_role": m.sender_role,
            "body": m.body,
            "is_mine": m.sender_signup_id == student.id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in res.scalars().all()
    ]


async def post_student_message(
    db: AsyncSession,
    student: SignupRequest,
    thread_id: str,
    body: str,
) -> dict:
    await _require_student(student)
    text = (body or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if len(text) > 4000:
        raise HTTPException(status_code=400, detail="Message too long (max 4000 characters)")

    thread_res = await db.execute(
        select(StudentMentoringThread).where(
            StudentMentoringThread.id == thread_id,
            StudentMentoringThread.student_signup_id == student.id,
        )
    )
    thread = thread_res.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    now = datetime.now(timezone.utc)
    msg = StudentMentoringMessage(
        thread_id=thread.id,
        sender_signup_id=student.id,
        sender_role="student",
        body=text,
        created_at=now,
    )
    thread.updated_at = now
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return {
        "id": msg.id,
        "sender_label": "You",
        "sender_role": "student",
        "body": msg.body,
        "is_mine": True,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


async def _circle_role_for_user(db: AsyncSession, user_id: str, circle_id: Optional[str]) -> Optional[str]:
    if not circle_id:
        return None
    res = await db.execute(
        select(CircleMember).where(
            CircleMember.user_id == user_id,
            CircleMember.circle_id == circle_id,
        )
    )
    cm = res.scalar_one_or_none()
    if not cm:
        return None
    if cm.role in ("lead", "leader"):
        return "leader"
    return "member"


async def _mentor_assigned_circle_ids(db: AsyncSession, mentor_id: str) -> set[str]:
    res = await db.execute(select(MentorProfile).where(MentorProfile.id == mentor_id))
    profile = res.scalar_one_or_none()
    if not profile:
        return set()
    ids: set[str] = set()
    if profile.circle_id:
        ids.add(profile.circle_id)
    if profile.assigned_circles:
        ids.update(c for c in profile.assigned_circles if c)
    return ids


async def _require_mentoring_reply_access(
    db: AsyncSession,
    sender: SignupRequest,
    thread: StudentMentoringThread,
) -> str:
    """Return sender_role after verifying the caller may reply in this thread."""
    if sender.persona == Persona.mentor:
        assigned = await _mentor_assigned_circle_ids(db, sender.id)
        if not thread.circle_id or thread.circle_id not in assigned:
            raise HTTPException(status_code=403, detail="You are not assigned to this student's circle")
        return "mentor"
    if sender.persona in (Persona.sponsor_leader, Persona.sponsor_member):
        circle_role = await _circle_role_for_user(db, sender.id, thread.circle_id)
        if not circle_role:
            raise HTTPException(status_code=403, detail="You are not in this student's circle")
        return circle_role
    raise HTTPException(status_code=403, detail="Only mentors or circle members can reply")


async def post_mentor_reply(
    db: AsyncSession,
    sender: SignupRequest,
    thread_id: str,
    body: str,
) -> dict:
    """Circle mentor, member, or leader replies in a student mentoring thread."""
    text = (body or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    thread_res = await db.execute(select(StudentMentoringThread).where(StudentMentoringThread.id == thread_id))
    thread = thread_res.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    sender_role = await _require_mentoring_reply_access(db, sender, thread)

    now = datetime.now(timezone.utc)
    msg = StudentMentoringMessage(
        thread_id=thread.id,
        sender_signup_id=sender.id,
        sender_role=sender_role,
        body=text,
        created_at=now,
    )
    thread.updated_at = now
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return {
        "id": msg.id,
        "sender_label": _sender_label(sender_role),
        "sender_role": sender_role,
        "body": msg.body,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
