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


async def post_circle_kia_briefing(db: AsyncSession, circle_id: str, text: str) -> None:
    if not circle_id or not text.strip():
        return
    channel_res = await db.execute(
        select(ChatChannel)
        .where(ChatChannel.circle_id == circle_id)
        .order_by(ChatChannel.created_at)
        .limit(1)
    )
    channel = channel_res.scalar_one_or_none()
    if not channel:
        return
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
        return

    prof_res = await db.execute(
        select(SchoolProfile.school_name).where(SchoolProfile.id == school_id)
    )
    school_name = prof_res.scalar_one_or_none() or "School"

    summary = _narrative_snippet(narrative)
    circle_line = (
        f"**Circle:** {student.circle_name}\n" if student.circle_name else ""
    )

    school_text = (
        f"📊 **Report published** — {quarter} · {fy}\n\n"
        f"**Student:** {student.full_name} · **Grade:** {student.grade}\n"
        f"**Submitted by:** {teacher_name}\n"
        f"**Attendance:** {int(student.attendance_pct or 0)}% · "
        f"**Avg score:** {int(student.avg_score or 0)}%\n"
        f"**ZQA composite:** {int(student.zqa_score or 0)}\n"
        f"{circle_line}\n"
        f"**Kia summary:** {summary}\n\n"
        f"View details under **Students → Reports**."
    )

    try:
        await post_school_kia_briefing(db, school_id, school_text)
        if student.circle_id:
            circle_text = (
                f"📊 **School report published** — {school_name}\n\n"
                f"**Student:** {student.full_name} ({student.grade})\n"
                f"**Quarter:** {quarter} · **FY:** {fy}\n"
                f"**ZQA:** {int(student.zqa_score or 0)} · "
                f"**Attendance:** {int(student.attendance_pct or 0)}%\n\n"
                f"**Summary:** {summary}"
            )
            await post_circle_kia_briefing(db, student.circle_id, circle_text)
    except Exception:
        logger.exception("Kia report_published briefing failed")


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


async def emit_member_joined(
    db: AsyncSession,
    *,
    circle: SponsorCircle,
    member_name: str,
    leader_name: str,
    role_label: str = "Sponsor member",
) -> None:
    text = (
        f"👋 **New circle member**\n\n"
        f"**{member_name}** ({role_label}) joined **{circle.name}** after leader approval.\n"
        f"**Approved by:** {leader_name}\n\n"
        f"Welcome them in **Chat & Kia** and share your invite link for more sponsors."
    )
    try:
        await post_circle_kia_briefing(db, circle.id, text)
    except Exception:
        logger.exception("Kia member_joined briefing failed")


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
