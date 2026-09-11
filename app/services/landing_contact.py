"""Landing page contact form — store inquiries, notify inbox, thank the submitter."""

from __future__ import annotations

import logging

from app.core.settings import settings
from app.db.session import SessionLocal
from app.services.email import send_email
from app.services.email_templates import (
    render_landing_contact_thank_you_html,
    render_waitlist_interest_thank_you_html,
)
from app.services.landing_contact_store import (
    mark_inquiry_email_notified,
    mark_inquiry_thank_you_sent,
)

logger = logging.getLogger(__name__)


async def notify_landing_contact_inquiry(
    *,
    name: str,
    email: str,
    interest: str,
    message: str,
    visitor_meta: dict | None = None,
) -> bool:
    """
    Deliver a website contact submission to the configured landing inbox.
    Returns True when email was sent; False when SMTP is off or send failed.
    """
    to_email = (settings.landing_contact_to or "harsh@zenkimpact.com,vinayak@zenkimpact.com").strip()
    subject = f"[ZENK Website] {interest} — {name}"
    body = (message or "").strip() or "(No message provided.)"
    meta = visitor_meta or {}
    geo_bits = [
        meta.get("geo_city"),
        meta.get("geo_region"),
        meta.get("geo_country"),
    ]
    geo = ", ".join(p for p in geo_bits if p) or "—"
    text_body = (
        "New message from the ZENK landing / waitlist interest form.\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Interest: {interest}\n"
        f"IP: {meta.get('ip_address') or '—'}\n"
        f"Location: {geo}\n"
        f"Path: {meta.get('landing_path') or '—'}\n"
        f"Timezone: {meta.get('timezone') or '—'}\n\n"
        "Message:\n"
        f"{body}\n"
    )

    if not (settings.smtp_enabled or settings.resend_api_key):
        logger.warning(
            "Landing contact notification skipped (email disabled — set RESEND_API_KEY or SMTP_ENABLED): "
            "name=%s email=%s interest=%s",
            name,
            email,
            interest,
        )
        return False

    try:
        await send_email(
            subject=subject,
            to_email=to_email,
            text_body=text_body,
        )
        return True
    except Exception:
        logger.exception(
            "Landing contact notification failed for submitter email=%s interest=%s",
            email,
            interest,
        )
        return False


async def send_waitlist_interest_thank_you(
    *,
    name: str,
    email: str,
    interest: str,
) -> bool:
    """Confirmation email to the person who registered interest."""
    if not (settings.smtp_enabled or settings.resend_api_key):
        logger.warning(
            "Waitlist thank-you skipped (email disabled): email=%s",
            email,
        )
        return False

    first = (name or "").strip().split()[0] if (name or "").strip() else "there"
    subject = "You're on the ZenK founding list"
    text_body = (
        f"Hi {first},\n\n"
        "Thank you for registering your interest with ZenK Impact.\n\n"
        "He almost stopped dreaming. A circle refused to let him.\n"
        "From a Rajasthan classroom to an engineer who now lifts the next child — "
        "that is the kind of story Founding Circles exist to write.\n\n"
        "What happens next:\n"
        "1. Acknowledgement within 48 hours\n"
        "2. A short 20-minute call\n"
        "3. Circle formation\n"
        "4. Matching after the annual budget is committed\n"
        "5. Launch\n\n"
        f"Your interest: {interest}\n\n"
        "No commitment today — we'll be in touch soon.\n\n"
        "— The ZenK Impact team\n"
        "https://in.zenkimpact.com\n"
    )
    website = getattr(settings, "website_url", None) or getattr(
        settings, "frontend_base_url", None
    ) or "https://in.zenkimpact.com"

    try:
        html_body = render_waitlist_interest_thank_you_html(
            name=name,
            interest=interest,
            website_url=str(website),
        )
        await send_email(
            subject=subject,
            to_email=email,
            text_body=text_body,
            html_body=html_body,
        )
        return True
    except Exception:
        logger.exception("Waitlist thank-you email failed for email=%s", email)
        return False


async def send_landing_contact_thank_you(
    *,
    name: str,
    email: str,
    interest: str,
) -> bool:
    """Confirmation email for the homepage Get started form."""
    if not (settings.smtp_enabled or settings.resend_api_key):
        logger.warning(
            "Contact thank-you skipped (email disabled): email=%s",
            email,
        )
        return False

    first = (name or "").strip().split()[0] if (name or "").strip() else "there"
    subject = "We received your message — ZenK Impact"
    text_body = (
        f"Hi {first},\n\n"
        "Thank you for writing to ZenK Impact. We have received your message and "
        "a member of the team will reply shortly.\n\n"
        f"Your interest: {interest}\n\n"
        "If you need us sooner, write info@zenkimpact.com.\n\n"
        "— The ZenK Impact team\n"
        "https://in.zenkimpact.com\n"
    )
    website = getattr(settings, "website_url", None) or getattr(
        settings, "frontend_base_url", None
    ) or "https://in.zenkimpact.com"

    try:
        html_body = render_landing_contact_thank_you_html(
            name=name,
            interest=interest,
            website_url=str(website),
        )
        await send_email(
            subject=subject,
            to_email=email,
            text_body=text_body,
            html_body=html_body,
        )
        return True
    except Exception:
        logger.exception("Contact thank-you email failed for email=%s", email)
        return False


async def run_inquiry_followups_background(
    *,
    inquiry_id: str,
    name: str,
    email: str,
    interest: str,
    message: str,
    visitor_meta: dict | None,
    source: str,
) -> None:
    """Send team + thank-you mail after the HTTP response — never block the form."""
    try:
        notified = await notify_landing_contact_inquiry(
            name=name,
            email=email,
            interest=interest,
            message=message,
            visitor_meta=visitor_meta,
        )
        if notified:
            async with SessionLocal() as db:
                await mark_inquiry_email_notified(db, inquiry_id)
    except Exception:
        logger.exception("Background team notify failed inquiry_id=%s", inquiry_id)

    try:
        if source == "waitlist_interest":
            thank_you_sent = await send_waitlist_interest_thank_you(
                name=name,
                email=email,
                interest=interest,
            )
        else:
            thank_you_sent = await send_landing_contact_thank_you(
                name=name,
                email=email,
                interest=interest,
            )
        if thank_you_sent:
            async with SessionLocal() as db:
                await mark_inquiry_thank_you_sent(db, inquiry_id)
    except Exception:
        logger.exception("Background thank-you failed inquiry_id=%s", inquiry_id)
