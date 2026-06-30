"""Auto-add parent guardian to circle when student enrollment is approved."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember
from app.models.enums import KycStatus, MemberKind
from app.models.school import SchoolStudent
from app.models.signup import SignupRequest
from app.models.student_family import StudentFamilyLink
from app.services.circle_member_invite import build_invite_note, LEADER_APPROVED
from app.services.notifications import create_notification

logger = logging.getLogger(__name__)


async def provision_parent_after_student_enrollment(
    db: AsyncSession,
    *,
    school_student: SchoolStudent,
    circle_id: str,
) -> None:
    """Link school student to signup, update family link, add approved parent to circle."""
    signup_id = school_student.signup_request_id or school_student.zenk_id
    if signup_id and not school_student.signup_request_id:
        school_student.signup_request_id = signup_id

    if not signup_id:
        return

    link_res = await db.execute(
        select(StudentFamilyLink).where(StudentFamilyLink.student_signup_id == signup_id)
    )
    link = link_res.scalar_one_or_none()
    if not link:
        return

    link.circle_id = circle_id
    link.school_student_id = school_student.id
    link.updated_at = datetime.now(timezone.utc)

    parent_res = await db.execute(
        select(SignupRequest).where(SignupRequest.id == link.parent_signup_id)
    )
    parent = parent_res.scalar_one_or_none()
    if not parent or parent.member_kind != MemberKind.parent_guardian.value:
        return

    if parent.kyc_status != KycStatus.approved:
        logger.info(
            "Parent %s not yet KYC-approved — circle membership deferred",
            parent.id,
        )
        return

    existing = await db.execute(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == parent.id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(
            CircleMember(
                circle_id=circle_id,
                user_id=parent.id,
                role="sponsor",
            )
        )
        try:
            from app.chat.models import SponsorCircle
            from app.services.kia_event_briefings import emit_member_joined

            circle_res = await db.execute(
                select(SponsorCircle).where(SponsorCircle.id == circle_id)
            )
            circle = circle_res.scalar_one_or_none()
            if circle:
                await emit_member_joined(
                    db,
                    circle=circle,
                    member_name="Parent / guardian",
                    leader_name="Circle enrollment",
                    role_label="Parent",
                )
        except Exception:
            logger.exception("Kia parent provision briefing failed")

    parent.admin_note = build_invite_note(circle_id, leader_status=LEADER_APPROVED)
    parent.updated_at = datetime.now(timezone.utc)

    try:
        await create_notification(
            recipient_id=parent.id,
            recipient_type="user",
            notification_type="parent_circle_provisioned",
            title="You are now in your child's circle",
            message=(
                "Your child was approved for their sponsorship circle. "
                "You have been added as parent guardian member."
            ),
            related_entity_id=circle_id,
            related_entity_type="sponsor_circle",
            db=db,
        )
    except Exception:
        logger.exception("Failed to notify parent %s of circle provision", parent.id)
