"""Landing page contact form — store inquiries and notify the public info inbox."""

from __future__ import annotations

import logging

from app.core.settings import settings
from app.services.email import send_email

logger = logging.getLogger(__name__)


async def notify_landing_contact_inquiry(
    *,
    name: str,
    email: str,
    interest: str,
    message: str,
) -> bool:
    """
    Deliver a website contact submission to the configured landing inbox.
    Returns True when email was sent; False when SMTP is off or send failed.
    """
    to_email = (settings.landing_contact_to or "info@zenkimpact.com").strip()
    subject = f"[ZENK Website] {interest} — {name}"
    body = (message or "").strip() or "(No message provided.)"
    text_body = (
        "New message from the ZENK landing page contact form.\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Interest: {interest}\n\n"
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
