from __future__ import annotations

import smtplib
import logging
from email.message import EmailMessage
from functools import partial
from typing import Optional

import anyio

from app.core.settings import settings


logger = logging.getLogger(__name__)


def _send_email_sync(
    *, subject: str, to_email: str, text_body: str, html_body: Optional[str] = None
) -> None:
    """
    Synchronous SMTP send. Call via `send_email()` in async contexts.
    """
    if not settings.smtp_enabled:
        logger.info("SMTP disabled (SMTP_ENABLED=false). Skipping email to=%s subject=%s", to_email, subject)
        return

    if not settings.smtp_host:
        raise RuntimeError("SMTP is enabled but smtp_host is not configured")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.set_content(text_body)
    
    # Add HTML alternative if provided
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_starttls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)
    logger.info("Email sent to=%s subject=%s", to_email, subject)


async def send_email(
    *, subject: str, to_email: str, text_body: str, html_body: Optional[str] = None
) -> None:
    """Send email with optional HTML body."""
    await anyio.to_thread.run_sync(
        partial(
            _send_email_sync,
            subject=subject,
            to_email=to_email,
            text_body=text_body,
            html_body=html_body,
        )
    )


