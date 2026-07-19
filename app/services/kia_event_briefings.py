"""
Kia structured briefings for important platform events.

Posts to:
- School Kia panel (school_kia_messages, role=kia)
- Circle chat (chat_messages as Kia system persona)
- In-app notifications where action is required
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.gamified_persona import get_or_create_persona
from app.chat.models import ChatChannel, ChatMessage, CircleMember, GamifiedPersona, SponsorCircle
from app.models.notification import Notification
from app.models.school import SchoolKiaMessage, SchoolProfile, SchoolStudent
from app.models.signup import SignupRequest

logger = logging.getLogger(__name__)

KIA_SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"


def _short_id(entity_id: str) -> str:
    return f"{(entity_id or '')[:8]}…" if entity_id else "—"


async def _get_kia_persona(db: AsyncSession) -> GamifiedPersona:
    res = await db.execute(
        select(GamifiedPersona).where(GamifiedPersona.nickname == "Kia")
    )
    persona = res.scalar_one_or_none()
    if persona:
        return persona

    from app.models.enums import Persona as RP

    user_res = await db.execute(
        select(SignupRequest).where(SignupRequest.id == KIA_SYSTEM_USER_ID)
    )
    if not user_res.scalar_one_or_none():
        db.add(
            SignupRequest(
                id=KIA_SYSTEM_USER_ID,
                persona=RP.student,
                full_name="Kia AI",
                mobile="0000000000",
                email="kia@zenk.ai",
                password_hash="system_managed",
                address_line1="System",
                address_line2="System",
                city="Digital",
                state="Zenk",
                pincode="000000",
                country="India",
            )
        )
        await db.flush()

    persona = GamifiedPersona(
        user_id=KIA_SYSTEM_USER_ID,
        nickname="Kia",
        avatar_key="avatar_kia",
    )
    db.add(persona)
    await db.flush()
    return persona


async def post_school_kia_briefing(db: AsyncSession, school_id: str, text: str) -> None:
    if not school_id or not text.strip():
        return
    db.add(
        SchoolKiaMessage(
            id=str(uuid.uuid4()),
            school_id=school_id,
            role="kia",
            text=text.strip(),
        )
    )


async def post_admin_kia_briefing(
    db: AsyncSession,
    text: str,
    *,
    event_type: Optional[str] = None,
    action_path: Optional[str] = None,
) -> None:
    if not text.strip():
        return
    from app.services.kia_admin import post_admin_kia_briefing as _post

    await _post(db, text, event_type=event_type, action_path=action_path)


async def post_circle_kia_briefing(db: AsyncSession, circle_id: str, text: str) -> bool:
    """Post Kia message to circle #general. Creates the channel if missing. Returns True if posted."""
    if not circle_id or not text.strip():
        return False
    # Prefer public #general (or first non-DM channel)
    channel_res = await db.execute(
        select(ChatChannel)
        .where(
            ChatChannel.circle_id == circle_id,
            ChatChannel.dm_for.is_(None),
        )
        .order_by(ChatChannel.created_at)
    )
    channels = list(channel_res.scalars().all())
    channel = None
    for ch in channels:
        if (ch.name or "").strip().lower() in ("general", "main", "announcements"):
            channel = ch
            break
    if channel is None and channels:
        channel = channels[0]
    if not channel:
        from app.chat.models import ChannelType

        channel = ChatChannel(
            circle_id=circle_id,
            name="general",
            channel_type=ChannelType.persistent,
        )
        db.add(channel)
        await db.flush()

    kia = await _get_kia_persona(db)
    db.add(
        ChatMessage(
            id=str(uuid.uuid4()),
            channel_id=channel.id,
            gamified_persona_id=kia.id,
            content_text=text.strip(),
            shield_action="allow",
        )
    )
    return True


async def notify_circle_leads(
    db: AsyncSession,
    *,
    circle_id: str,
    title: str,
    message: str,
    notification_type: str,
    related_entity_id: Optional[str] = None,
    related_entity_type: Optional[str] = None,
) -> None:
    res = await db.execute(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.role.in_(("lead", "sponsor_leader", "sponsor", "coordinator")),
        )
    )
    for member in res.scalars().all():
        db.add(
            Notification(
                id=str(uuid.uuid4()),
                recipient_id=member.user_id,
                recipient_type="user",
                notification_type=notification_type,
                title=title,
                message=message,
                related_entity_id=related_entity_id,
                related_entity_type=related_entity_type,
            )
        )


async def notify_user(
    db: AsyncSession,
    *,
    user_id: str,
    title: str,
    message: str,
    notification_type: str,
    related_entity_id: Optional[str] = None,
    related_entity_type: Optional[str] = None,
) -> None:
    if not user_id:
        return
    db.add(
        Notification(
            id=str(uuid.uuid4()),
            recipient_id=user_id,
            recipient_type="user",
            notification_type=notification_type,
            title=title,
            message=message,
            related_entity_id=related_entity_id,
            related_entity_type=related_entity_type,
        )
    )


def _narrative_snippet(narrative: Optional[str], limit: int = 220) -> str:
    text = (narrative or "").strip().replace("\n", " ")
    if not text:
        return "No teacher narrative included."
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


# ── Enrollment ────────────────────────────────────────────────────────────────


async def emit_enrollment_submitted(
    db: AsyncSession,
    *,
    req: Any,
    school_name: str,
    school_user: SignupRequest,
) -> None:
    academic_note = ""
    if getattr(req, "initial_academic_payload", None):
        q = req.initial_academic_payload.get("quarter", "Q4")
        academic_note = f"\nInitial **{q}** academic data included — applies after approval."

    circle_text = (
        f"📋 **School enrollment intimation** — {school_name}\n\n"
        f"**Student:** {req.full_name} · **Grade:** {req.grade}\n"
        f"**Requested ZenK circle:** {req.circle_name}\n"
        f"**SL:** {req.sl_name or 'TBD'} · **Class teacher:** {req.class_teacher or 'TBD'}"
        f"{academic_note}\n\n"
        f"Please review in **School Comm → Enrollment requests** and Approve or Reject.\n"
        f"_Request ID: {_short_id(req.id)}_"
    )

    school_text = (
        f"📋 **Enrollment sent to circle**\n\n"
        f"**Student:** {req.full_name} · **Grade:** {req.grade}\n"
        f"**Circle:** {req.circle_name}\n"
        f"**Status:** Awaiting circle approval\n\n"
        f"Kia will notify you when {req.circle_name} approves or declines. "
        f"Track status under **Students → Enrollment requests**.\n"
        f"_Request ID: {_short_id(req.id)}_"
    )

    try:
        # Circle chat: school persona intimation (visible to sponsors in channel).
        persona = await get_or_create_persona(school_user, db)
        ch_res = await db.execute(
            select(ChatChannel)
            .where(ChatChannel.circle_id == req.circle_id)
            .order_by(ChatChannel.created_at)
            .limit(1)
        )
        ch = ch_res.scalar_one_or_none()
        if ch and persona:
            db.add(
                ChatMessage(
                    id=str(uuid.uuid4()),
                    channel_id=ch.id,
                    gamified_persona_id=persona.id,
                    content_text=circle_text,
                    shield_action="allow",
                )
            )
        # School dashboard: Kia confirmation + next steps.
        await post_school_kia_briefing(db, req.school_id, school_text)
        await notify_circle_leads(
            db,
            circle_id=req.circle_id,
            title="New school enrollment request",
            message=(
                f"{school_name} requested to enroll {req.full_name} ({req.grade}) "
                f"in {req.circle_name}. Approve in School Comm."
            ),
            notification_type="school_enrollment_request",
            related_entity_id=req.id,
            related_entity_type="school_enrollment",
        )
        req.intimation_sent_at = datetime.utcnow()
    except Exception:
        logger.exception("Kia enrollment_submitted briefing failed")


async def emit_enrollment_approved(
    db: AsyncSession,
    *,
    req: Any,
    student: SchoolStudent,
    reviewer: SignupRequest,
    school_name: Optional[str] = None,
) -> None:
    school_name = school_name or "Your school"
    reviewer_name = reviewer.full_name or "Circle reviewer"

    school_text = (
        f"✅ **Enrollment approved** — {req.circle_name}\n\n"
        f"**Student:** {student.full_name} · **Grade:** {student.grade}\n"
        f"**Approved by:** {reviewer_name}\n"
        f"**ZQA:** {int(student.zqa_score or 0)} · **Attendance:** {int(student.attendance_pct or 0)}%\n\n"
        f"The student is now on your dashboard. Submit quarterly reports to keep impact data current.\n"
        f"_Student ID: {_short_id(student.id)}_"
    )

    circle_text = (
        f"✅ **Student enrolled** — {school_name}\n\n"
        f"**{student.full_name}** ({student.grade}) is now a sponsored beneficiary in this circle.\n"
        f"Approved by **{reviewer_name}**.\n\n"
        f"Impact tracking, ZQA, and marketplace student-fund orders are now active for this student."
    )

    try:
        await post_school_kia_briefing(db, req.school_id, school_text)
        await post_circle_kia_briefing(db, req.circle_id, circle_text)
        if req.requested_by_user_id:
            await notify_user(
                db,
                user_id=req.requested_by_user_id,
                title="Enrollment approved",
                message=f"{req.circle_name} approved {student.full_name}.",
                notification_type="school_enrollment_approved",
                related_entity_id=student.id,
                related_entity_type="school_student",
            )
    except Exception:
        logger.exception("Kia enrollment_approved briefing failed")


async def emit_enrollment_rejected(
    db: AsyncSession,
    *,
    req: Any,
    reviewer: SignupRequest,
) -> None:
    reviewer_name = reviewer.full_name or "Circle reviewer"
    reason = (req.review_note or "").strip() or "No reason provided."

    school_text = (
        f"❌ **Enrollment declined** — {req.circle_name}\n\n"
        f"**Student:** {req.full_name} · **Grade:** {req.grade}\n"
        f"**Reviewed by:** {reviewer_name}\n"
        f"**Reason:** {reason}\n\n"
        f"You may revise and submit a new request or choose another circle.\n"
        f"_Request ID: {_short_id(req.id)}_"
    )

    circle_text = (
        f"❌ **Enrollment declined** — {req.full_name}\n\n"
        f"**School request rejected** by {reviewer_name}.\n"
        f"**Reason:** {reason}"
    )

    try:
        await post_school_kia_briefing(db, req.school_id, school_text)
        await post_circle_kia_briefing(db, req.circle_id, circle_text)
        if req.requested_by_user_id:
            await notify_user(
                db,
                user_id=req.requested_by_user_id,
                title="Enrollment not approved",
                message=f"{req.circle_name} declined {req.full_name}. {reason}",
                notification_type="school_enrollment_rejected",
                related_entity_id=req.id,
                related_entity_type="school_enrollment",
            )
    except Exception:
        logger.exception("Kia enrollment_rejected briefing failed")


# ── Reports & ZQA ─────────────────────────────────────────────────────────────


async def emit_report_published(
    db: AsyncSession,
    *,
    school_id: str,
    student: SchoolStudent,
    quarter: str,
    fy: str,
    teacher_name: str,
    narrative: Optional[str] = None,
    finalized: bool = True,
) -> None:
    if not finalized:
        return {
            "school_briefing": False,
            "circle_id": None,
            "circle_name": None,
            "circle_chat": False,
            "partner_thread": False,
        }

    from app.models.school import SchoolStudentSubjectScore
    from app.services.circle_school_partner import (
        ensure_student_circle_id,
        post_partner_message,
    )
    from app.services.student_circle_privacy import (
        pseudonym_for_signup,
        resolve_student_signup_for_school_row,
    )

    prof_res = await db.execute(
        select(SchoolProfile.school_name).where(SchoolProfile.id == school_id)
    )
    school_name = prof_res.scalar_one_or_none() or "School"

    summary = _narrative_snippet(narrative)
    attendance = int(student.attendance_pct or 0)
    avg_score = int(student.avg_score or 0)
    zqa = int(student.zqa_score or 0)
    q = (quarter or "Q4").upper()

    subj_res = await db.execute(
        select(SchoolStudentSubjectScore).where(
            SchoolStudentSubjectScore.student_id == student.id,
            SchoolStudentSubjectScore.quarter == q,
        )
    )
    subject_rows = list(subj_res.scalars().all())
    subject_preview = ""
    if subject_rows:
        parts = [
            f"{(r.subject or 'Subject').title()} {int(round(float(r.score or 0)))}%"
            for r in subject_rows[:8]
        ]
        subject_preview = " · ".join(parts)

    circle_name = (student.circle_name or "").strip()
    circle_line = f"**Circle:** {circle_name}\n" if circle_name else ""

    school_text = (
        f"📊 **Report published** — {q} · {fy}\n\n"
        f"**Student:** {student.full_name} · **Grade:** {student.grade}\n"
        f"**Submitted by:** {teacher_name}\n"
        f"**Attendance:** {attendance}% · **Avg score:** {avg_score}%\n"
        f"**ZQA composite:** {zqa}\n"
        f"{circle_line}"
        f"{('**Subjects:** ' + subject_preview + chr(10)) if subject_preview else ''}"
        f"\n**Kia summary:** {summary}\n\n"
        f"View details under **Students → Reports**."
    )

    result = {
        "school_briefing": False,
        "circle_id": None,
        "circle_name": (student.circle_name or "").strip() or None,
        "circle_chat": False,
        "partner_thread": False,
    }

    try:
        await post_school_kia_briefing(db, school_id, school_text)
        result["school_briefing"] = True

        circle_id = await ensure_student_circle_id(db, student)
        result["circle_id"] = circle_id
        if student.circle_name:
            result["circle_name"] = student.circle_name
        if not circle_id:
            return result

        signup = await resolve_student_signup_for_school_row(db, student)
        display_name = (
            await pseudonym_for_signup(db, signup) if signup else (student.circle_name or "Student")
        )

        circle_text = (
            f"📋 **ZenK progress transcript** — {school_name}\n"
            f"**Quarter {q}** · FY {fy}\n\n"
            f"**Student:** {display_name} · Grade {student.grade or '—'}\n"
            f"**Circle:** {student.circle_name or '—'}\n\n"
            f"**Key metrics**\n"
            f"• Attendance: {attendance}%\n"
            f"• Avg academic: {avg_score}%\n"
            f"• ZQA: {zqa}\n"
            f"• Risk: {student.risk_level or '—'}\n"
            f"{('• Subjects: ' + subject_preview + chr(10)) if subject_preview else ''}"
            f"\n**Teacher summary:** {summary}\n\n"
            f"_Official school transcript shared with circle leaders and members._"
        )
        result["circle_chat"] = await post_circle_kia_briefing(db, circle_id, circle_text)

        # Also surface in school ↔ leader partner messaging thread
        try:
            await post_partner_message(
                db,
                circle_id=circle_id,
                school_id=school_id,
                sender_side="school",
                body=circle_text,
                sender_name="Kia · School reports",
            )
            result["partner_thread"] = True
        except Exception:
            logger.exception("Partner-thread report preview failed")
    except Exception:
        logger.exception("Kia report_published briefing failed")

    return result


# ── Circle operations ─────────────────────────────────────────────────────────


async def emit_budget_updated(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    leader: SignupRequest,
    annual_budget: int,
    fy_label: Optional[str],
) -> None:
    fy = fy_label or circle.fy_label or "2025-26"
    leader_name = leader.full_name or "Circle leader"
    text = (
        f"💰 **Circle budget updated**\n\n"
        f"**Set by:** {leader_name}\n"
        f"**Annual budget:** ₹{annual_budget:,}\n"
        f"**Financial year:** FY {fy}\n\n"
        f"Members can view the tracker on **My Circle → Budget**. "
        f"Balance to spend updates as marketplace orders are placed."
    )
    try:
        await post_circle_kia_briefing(db, circle.id, text)
        await notify_circle_leads(
            db,
            circle_id=circle.id,
            title="Circle budget updated",
            message=f"{leader_name} set FY {fy} budget to ₹{annual_budget:,}.",
            notification_type="circle_budget_updated",
            related_entity_id=circle.id,
            related_entity_type="sponsor_circle",
        )
    except Exception:
        logger.exception("Kia budget_updated briefing failed")


def _format_inr(amount: Optional[int]) -> str:
    try:
        return f"₹{int(amount or 0):,}"
    except (TypeError, ValueError):
        return "₹0"


def _friendly_student_label(raw: Optional[str], index: int = 0) -> str:
    """Never show raw UUIDs / emails as the sponsored-child label in chat."""
    label = (raw or "").strip()
    if not label:
        return f"Sponsored student {index + 1}"
    # UUID / long opaque ids → soft label
    compact = label.replace("-", "")
    if len(label) >= 32 and compact.isalnum():
        return f"Sponsored student {index + 1}"
    if "@" in label:
        return f"Sponsored student {index + 1}"
    return label


def _strip_kia_suggests_prefix(text: Optional[str]) -> Optional[str]:
    """
    Chat UI wraps everything after 'Kia suggests:' into a suggestion card.
    Welcome messages must never use that marker — strip it if the LLM adds it.
    """
    if not text:
        return text
    cleaned = text.strip().strip('"').strip("'")
    for marker in ("Kia suggests:", "Kia Suggests:", "kia suggests:"):
        idx = cleaned.lower().find(marker.lower())
        if idx >= 0:
            before = cleaned[:idx].strip()
            after = cleaned[idx + len(marker) :].strip()
            cleaned = " ".join(p for p in (before, after) if p).strip()
    return cleaned or None


def _build_child_snapshot_lines(students: list[dict]) -> list[str]:
    """Masked student snapshot lines safe for circle chat."""
    if not students:
        return []

    lines: list[str] = []
    for idx, st in enumerate(students[:3]):
        name = _friendly_student_label(
            st.get("pseudonym") or st.get("masked_name"),
            index=idx,
        )
        grade = st.get("grade") or "—"
        zqa = st.get("zqa_score", st.get("zenq_score"))
        attendance = st.get("attendance_pct")
        bits = [f"**{name}** · Grade {grade}"]
        metrics: list[str] = []
        if zqa is not None:
            metrics.append(f"ZQA {int(zqa)}")
        if attendance is not None:
            metrics.append(f"attendance {int(attendance)}%")
        if metrics:
            bits.append(" · ".join(metrics))
        lines.append(f"· {' · '.join(bits)}")

    if len(students) > 3:
        lines.append(f"· _+{len(students) - 3} more sponsored student(s) on the circle roster_")
    return lines


async def _compose_member_welcome_text(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    member_name: str,
    leader_name: str,
    role_label: str,
    member_user_id: Optional[str] = None,
    welcome_kind: str = "member",
) -> str:
    """
    Warm Kia welcome for a new circle member.

    Includes a gentle circle snapshot and, when a child/student is enrolled,
    a privacy-safe progress snapshot.
    """
    from app.services.kia_context import (
        _fetch_circle_budget,
        _fetch_circle_students,
        _fetch_pending_enrollments,
    )

    member_count_res = await db.execute(
        select(CircleMember).where(CircleMember.circle_id == circle.id)
    )
    member_count = len(list(member_count_res.scalars().all()))

    students = await _fetch_circle_students(circle.id, db)
    pending = await _fetch_pending_enrollments(circle.id, db)
    budget = None
    if member_user_id:
        budget = await _fetch_circle_budget(circle.id, member_user_id, db)
    if budget is None:
        budget = await _fetch_circle_budget(circle.id, KIA_SYSTEM_USER_ID, db)

    # Prefer a short LLM welcome when available; always fall back to a warm template.
    # Never keep "Kia suggests:" — MessageBubble treats that as a suggestion card.
    llm_opener: Optional[str] = None
    try:
        from app.services.kia import handle_proactive_trigger

        llm_opener = await handle_proactive_trigger(
            "new_member_joined",
            {
                "member_name": member_name,
                "circle_name": circle.name,
                "member_count": member_count,
                "role_label": role_label,
                "has_sponsored_students": bool(students),
                "welcome_kind": welcome_kind,
            },
        )
        llm_opener = _strip_kia_suggests_prefix(llm_opener)
        if llm_opener and len(llm_opener) > 280:
            llm_opener = llm_opener[:277].rstrip() + "…"
    except Exception:
        logger.exception("Kia LLM welcome opener failed; using template")

    if welcome_kind == "parent":
        greeting = (
            llm_opener
            or (
                f"Welcome, **{member_name}** — we're glad you're here with your child's circle. "
                f"**{circle.name}** is a caring space for sponsors, mentors, and families walking this journey together."
            )
        )
        headline = "💛 **Welcome, parent / guardian**"
    else:
        greeting = (
            llm_opener
            or (
                f"Welcome to **{circle.name}**, **{member_name}**! "
                f"We're so glad you're here — this circle grows stronger with every caring member who joins."
            )
        )
        headline = "💛 **Welcome to the circle**"

    parts = [
        headline,
        "",
        greeting,
        "",
        f"**Joined as:** {role_label}",
        f"**Welcomed by:** {leader_name}",
        f"**Circle family:** {member_count} member{'s' if member_count != 1 else ''}",
    ]

    if budget and int(budget.get("total_budget") or 0) > 0:
        fy = budget.get("fy_label") or circle.fy_label or "this FY"
        parts.extend(
            [
                "",
                "**Circle snapshot**",
                f"· FY budget: {_format_inr(budget.get('total_budget'))} ({fy})",
                f"· Balance to spend: {_format_inr(budget.get('balance_to_spend') or budget.get('available_balance'))}",
            ]
        )
    elif budget:
        parts.extend(
            [
                "",
                "**Circle snapshot**",
                "· Budget tracker is ready — your leader can set the FY target anytime.",
            ]
        )

    child_lines = _build_child_snapshot_lines(students)
    if child_lines:
        parts.extend(
            [
                "",
                "**Your circle's sponsored child snapshot**",
                *child_lines,
                "",
                "Open **Student** or ask **@Kia** anytime for a gentler deep-dive on progress, ZQA, and next steps.",
            ]
        )
    else:
        parts.extend(
            [
                "",
                "No sponsored student is linked yet — when a child is enrolled, I'll share a soft progress snapshot here so the whole circle can celebrate together.",
            ]
        )
        if pending:
            parts.append(
                f"There {'is' if pending == 1 else 'are'} **{pending}** enrollment request"
                f"{'' if pending == 1 else 's'} waiting for leader review in **School Comm**."
            )

    parts.extend(
        [
            "",
            "Say hello in **Chat & Kia**, explore **My Circle**, and tag **@Kia** whenever you need a calm guide. "
            "You're among friends now — welcome home. 🌿",
        ]
    )
    return "\n".join(parts)


async def emit_member_joined(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    member_name: str,
    leader_name: str,
    role_label: str = "Sponsor member",
    member_user_id: Optional[str] = None,
    welcome_kind: str = "member",
) -> None:
    try:
        text = await _compose_member_welcome_text(
            db,
            circle=circle,
            member_name=member_name,
            leader_name=leader_name,
            role_label=role_label,
            member_user_id=member_user_id,
            welcome_kind=welcome_kind,
        )
        await post_circle_kia_briefing(db, circle.id, text)
    except Exception:
        logger.exception("Kia member_joined briefing failed")
        # Last-resort short welcome so join never stays silent.
        try:
            await post_circle_kia_briefing(
                db,
                circle.id,
                (
                    f"💛 **Welcome to {circle.name}**, **{member_name}**!\n\n"
                    f"You're in as **{role_label}**. Say hello in Chat & Kia — "
                    f"I'm here whenever you need a gentle guide."
                ),
            )
        except Exception:
            logger.exception("Kia member_joined fallback briefing also failed")


async def emit_circle_renamed(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    leader_name: str,
    old_name: str,
) -> None:
    text = (
        f"✏️ **Circle renamed**\n\n"
        f"**{leader_name}** updated the circle name.\n"
        f"**Previous:** {old_name}\n"
        f"**Now:** {circle.name}"
    )
    try:
        await post_circle_kia_briefing(db, circle.id, text)
    except Exception:
        logger.exception("Kia circle_renamed briefing failed")


async def emit_marketplace_transaction(
    db: AsyncSession,
    *,
    circle_id: Optional[str],
    circle_name: Optional[str],
    buyer_name: str,
    order_lines: list[str],
    total_inr: int,
    order_type: str,
) -> None:
    if not circle_id and circle_name:
        res = await db.execute(
            select(SponsorCircle.id).where(SponsorCircle.name == circle_name).limit(1)
        )
        circle_id = res.scalar_one_or_none()

    if not circle_id:
        return

    lines = "\n".join(f"· {line}" for line in order_lines[:5])
    extra = f"\n_+{len(order_lines) - 5} more items_" if len(order_lines) > 5 else ""
    fund_label = "Student fund" if order_type == "student" else "Personal"

    text = (
        f"🛒 **Marketplace {fund_label} order**\n\n"
        f"**Placed by:** {buyer_name}\n"
        f"**Total:** ₹{total_inr:,}\n"
        f"{lines}{extra}\n\n"
        f"Track spend on **My Circle → Budget** and **Vendor Payments**."
    )
    try:
        await post_circle_kia_briefing(db, circle_id, text)
    except Exception:
        logger.exception("Kia marketplace_transaction briefing failed")


# ── School onboarding ─────────────────────────────────────────────────────────


async def emit_school_onboarded(
    db: AsyncSession,
    *,
    profile: SchoolProfile,
    principal_name: str,
) -> None:
    text = (
        f"🏫 **Welcome to ZenK School Portal**\n\n"
        f"**{profile.school_name}** is now an active partner school.\n"
        f"**Principal:** {principal_name}\n"
        f"**Code:** {profile.school_code or '—'}\n\n"
        f"**Kia recommends:** Add your first student, link them to a sponsor circle, "
        f"and submit a quarterly report when ready.\n\n"
        f"Use **Students → Add student** to start the enrollment flow."
    )
    try:
        await post_school_kia_briefing(db, profile.id, text)
    except Exception:
        logger.exception("Kia school_onboarded briefing failed")


# ── Membership admin ops ──────────────────────────────────────────────────────


async def emit_admin_circle_ops_submitted(
    db: AsyncSession,
    *,
    req: Any,
    circle_name: Optional[str] = None,
) -> None:
    circle_name = circle_name or "a circle"
    if req.request_type == "member_removal":
        text = (
            f"Circle ops — removal request pending review.\n"
            f"Circle: {circle_name}\n"
            f"Remove: {req.target_user_name}\n"
            f"Requested by: {req.requested_by_name}\n"
            f"Reason: {req.leader_comment}"
        )
        event_type = "member_removal_pending"
    else:
        text = (
            f"Circle ops — member limit increase pending review.\n"
            f"Circle: {circle_name}\n"
            f"Requested cap: {req.requested_limit} (current {req.current_member_limit})\n"
            f"Requested by: {req.requested_by_name}\n"
            f"Reason: {req.leader_comment}"
        )
        event_type = "member_limit_pending"
    try:
        await post_admin_kia_briefing(
            db, text, event_type=event_type, action_path="/dashboard/circle-ops"
        )
    except Exception:
        logger.exception("Admin Kia circle_ops_submitted briefing failed")


async def emit_admin_circle_ops_reviewed(
    db: AsyncSession,
    *,
    req: Any,
    circle_name: Optional[str] = None,
    decision: str,
) -> None:
    circle_name = circle_name or "a circle"
    label = "approved" if decision == "approved" else "rejected"
    text = (
        f"Circle ops {label} — {circle_name}\n"
        f"Type: {req.request_type}\n"
        f"ZenK note: {req.admin_comment}"
    )
    try:
        await post_admin_kia_briefing(
            db, text, event_type=f"circle_ops_{label}", action_path="/dashboard/circle-ops"
        )
    except Exception:
        logger.exception("Admin Kia circle_ops_reviewed briefing failed")


async def emit_member_removal_processed(
    db: AsyncSession,
    *,
    req: Any,
    circle_name: Optional[str] = None,
) -> None:
    circle_name = circle_name or "your circle"
    text = (
        f"👤 **Member removal approved** — {circle_name}\n\n"
        f"**Removed:** {req.target_user_name}\n"
        f"**Requested by:** {req.requested_by_name}\n"
        f"**ZenK note:** {req.admin_comment}\n\n"
        f"The member no longer has access to this circle."
    )
    try:
        await post_circle_kia_briefing(db, req.circle_id, text)
        if req.target_user_id:
            await notify_user(
                db,
                user_id=req.target_user_id,
                title="Removed from sponsor circle",
                message=f"You were removed from {circle_name}. {req.admin_comment}",
                notification_type="circle_member_removed",
            )
    except Exception:
        logger.exception("Kia member_removal_processed briefing failed")


async def emit_member_limit_approved(
    db: AsyncSession,
    *,
    req: Any,
    circle_name: Optional[str] = None,
) -> None:
    circle_name = circle_name or "your circle"
    text = (
        f"📈 **Member limit increased** — {circle_name}\n\n"
        f"**New cap:** {req.requested_limit} members "
        f"(was {req.current_member_limit})\n"
        f"**Requested by:** {req.requested_by_name}\n"
        f"**ZenK note:** {req.admin_comment}\n\n"
        f"You can approve new members up to the new limit."
    )
    try:
        await post_circle_kia_briefing(db, req.circle_id, text)
        await notify_circle_leads(
            db,
            circle_id=req.circle_id,
            title="Member limit approved",
            message=f"ZenK approved {req.requested_limit} members for {circle_name}.",
            notification_type="circle_member_limit_approved",
        )
    except Exception:
        logger.exception("Kia member_limit_approved briefing failed")
