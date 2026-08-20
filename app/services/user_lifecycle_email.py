"""User lifecycle emails — KYC decisions, member circle gate, branded timelines."""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import CircleMember, SponsorCircle
from app.core.settings import settings
from app.models.enums import MemberKind, Persona
from app.models.signup import SignupRequest
from app.services.circle_budget import LEADER_ROLES
from app.services.circle_member_invite import parse_invite_note
from app.services.email import send_email
from app.services.email_templates import (
    render_leader_member_ready_html,
    render_member_circle_decision_html,
    render_user_approval_html,
    render_user_info_required_html,
    render_user_rejected_html,
)

logger = logging.getLogger(__name__)

PERSONA_LABELS = {
    Persona.sponsor: "Sponsor",
    Persona.sponsor_leader: "Sponsor Leader",
    Persona.sponsor_member: "Circle Member",
    Persona.vendor: "Vendor",
    Persona.mentor: "Mentor",
    Persona.student: "Student",
    Persona.school: "School Partner",
}


def persona_label_for_signup(signup: SignupRequest) -> str:
    if (
        signup.persona == Persona.sponsor_member
        and getattr(signup, "member_kind", None) == MemberKind.parent_guardian.value
    ):
        return "Parent / guardian"
    return PERSONA_LABELS.get(signup.persona, "User")


async def resolve_invite_circle(
    db: AsyncSession, signup: SignupRequest
) -> tuple[Optional[str], Optional[str]]:
    """Return (circle_id, circle_name) from invite note when present."""
    circle_id, _, _ = parse_invite_note(signup.admin_note)
    if not circle_id:
        return None, None
    res = await db.execute(select(SponsorCircle).where(SponsorCircle.id == circle_id))
    circle = res.scalar_one_or_none()
    return circle_id, (circle.name if circle else None)


async def leader_emails_for_circle(db: AsyncSession, circle_id: str) -> list[str]:
    res = await db.execute(
        select(SignupRequest.email)
        .join(CircleMember, CircleMember.user_id == SignupRequest.id)
        .where(
            CircleMember.circle_id == circle_id,
            CircleMember.role.in_(list(LEADER_ROLES)),
        )
    )
    out: list[str] = []
    seen: set[str] = set()
    for (email,) in res.all():
        addr = (email or "").strip()
        if not addr:
            continue
        key = addr.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(addr)
    return out


async def send_kyc_decision_emails(
    *,
    db: AsyncSession,
    signup: SignupRequest,
    review_note: Optional[str],
) -> None:
    """Send applicant (and leader, when relevant) emails after an admin KYC decision."""
    label = persona_label_for_signup(signup)
    website = settings.website_url
    logo = settings.email_logo_url
    first = (signup.full_name or "").strip().split(" ")[0] or "there"
    status = signup.kyc_status.value if hasattr(signup.kyc_status, "value") else str(signup.kyc_status)

    try:
        if status == "approved":
            circle_id, circle_name = await resolve_invite_circle(db, signup)
            is_member = signup.persona == Persona.sponsor_member and bool(circle_id)

            if is_member:
                subject = f"Identity verified — waiting on your circle leader · {circle_name or 'Zenk'}"
                text_body = (
                    f"Hello {signup.full_name},\n\n"
                    f"Zenk has verified your identity as a {label}.\n"
                    f"One step remains: your circle leader must approve your membership"
                    f"{f' in {circle_name}' if circle_name else ''}.\n\n"
                    f"Sign in to check status: {website}/login\n\n"
                    "Regards,\nZenk Team\n"
                )
                html_body = render_user_approval_html(
                    full_name=signup.full_name,
                    persona_label=label,
                    website_url=website,
                    logo_url=logo,
                    flow="member_awaiting_leader",
                    circle_name=circle_name,
                    review_note=None,
                )
            else:
                subject = f"Your Zenk {label} KYC is Approved"
                text_body = (
                    f"Hello {signup.full_name},\n\n"
                    f"Your {label} registration on Zenk has been approved.\n\n"
                    f"Please login to Zenk ({website}) with your password.\n\n"
                    "Regards,\nZenk Team\n"
                )
                html_body = render_user_approval_html(
                    full_name=signup.full_name,
                    persona_label=label,
                    website_url=website,
                    logo_url=logo,
                    flow="standard",
                    circle_name=None,
                    review_note=None,
                )

            await send_email(
                subject=subject,
                to_email=signup.email,
                text_body=text_body,
                html_body=html_body,
            )

            if is_member and circle_id:
                leaders = await leader_emails_for_circle(db, circle_id)
                if leaders:
                    leader_html = render_leader_member_ready_html(
                        member_name=signup.full_name,
                        member_email=signup.email,
                        circle_name=circle_name or "your circle",
                        website_url=website,
                        logo_url=logo,
                    )
                    await send_email(
                        subject="A member is ready for your approval",
                        to_email=leaders,
                        text_body=(
                            f"{signup.full_name} ({signup.email}) passed Zenk verification and is "
                            f"waiting for your approval to join {circle_name or 'your circle'}.\n\n"
                            f"Review pending members: {website}/login\n"
                        ),
                        html_body=leader_html,
                        send_individually=True,
                    )

        elif status == "info_required":
            note = (review_note or "").strip() or "Please sign in and upload the documents we requested."
            subject = "Zenk needs a little more information"
            text_body = (
                f"Hello {signup.full_name},\n\n"
                f"We need additional information to finish verifying your {label} registration.\n\n"
                f"What we need:\n{note}\n\n"
                f"Sign in to upload: {website}/login\n\n"
                "Regards,\nZenk Team\n"
            )
            html_body = render_user_info_required_html(
                full_name=signup.full_name,
                persona_label=label,
                review_note=note,
                website_url=website,
                logo_url=logo,
            )
            await send_email(
                subject=subject,
                to_email=signup.email,
                text_body=text_body,
                html_body=html_body,
            )

        elif status == "rejected":
            note = (review_note or "").strip()
            subject = f"Update on your Zenk {label} application"
            text_body = (
                f"Hello {signup.full_name},\n\n"
                f"Your {label} registration was not approved at this time.\n"
                + (f"\nNote from our team:\n{note}\n" if note else "")
                + f"\nYou can sign in for details or contact support: {website}/login\n\n"
                "Regards,\nZenk Team\n"
            )
            html_body = render_user_rejected_html(
                full_name=signup.full_name,
                persona_label=label,
                review_note=note,
                website_url=website,
                logo_url=logo,
            )
            await send_email(
                subject=subject,
                to_email=signup.email,
                text_body=text_body,
                html_body=html_body,
            )
    except Exception:
        logger.exception(
            "Failed lifecycle email for signup_id=%s status=%s",
            signup.id,
            status,
        )


async def send_member_leader_decision_email(
    *,
    applicant: SignupRequest,
    circle_name: str,
    approved: bool,
) -> None:
    label = persona_label_for_signup(applicant)
    website = settings.website_url
    try:
        if approved:
            subject = f"Welcome to {circle_name} on Zenk"
            text_body = (
                f"Hello {applicant.full_name},\n\n"
                f"Your circle leader approved your membership in {circle_name}. "
                "You can now open your circle dashboard.\n\n"
                f"Sign in: {website}/login\n\n"
                "Regards,\nZenk Team\n"
            )
        else:
            subject = f"Update on joining {circle_name}"
            text_body = (
                f"Hello {applicant.full_name},\n\n"
                f"Your request to join {circle_name} was not accepted by the circle leader.\n\n"
                f"Sign in for details: {website}/login\n\n"
                "Regards,\nZenk Team\n"
            )
        html_body = render_member_circle_decision_html(
            full_name=applicant.full_name,
            persona_label=label,
            circle_name=circle_name,
            approved=approved,
            website_url=website,
            logo_url=settings.email_logo_url,
        )
        await send_email(
            subject=subject,
            to_email=applicant.email,
            text_body=text_body,
            html_body=html_body,
        )
    except Exception:
        logger.exception(
            "Failed leader-decision email for member signup_id=%s approved=%s",
            applicant.id,
            approved,
        )
