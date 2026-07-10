from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from functools import partial
from typing import Optional

import anyio
import httpx

from app.core.settings import settings


logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _email_enabled() -> bool:
    return bool(settings.smtp_enabled or settings.resend_api_key)


def _send_via_resend(
    *, subject: str, to_email: str, text_body: str, html_body: Optional[str] = None
) -> None:
    """Send via Resend HTTPS API (Railway-safe — port 443)."""
    api_key = (settings.resend_api_key or "").strip()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")

    payload: dict = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body

    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(f"Resend API error {response.status_code}: {detail}")

    logger.info("Email sent via Resend to=%s subject=%s", to_email, subject)


def _send_email_sync(
    *, subject: str, to_email: str, text_body: str, html_body: Optional[str] = None
) -> None:
    """
    Synchronous send. Prefer Resend HTTPS on Railway; fall back to SMTP locally.
    """
    if not _email_enabled():
        logger.info(
            "Email disabled (SMTP_ENABLED=false and no RESEND_API_KEY). Skipping to=%s subject=%s",
            to_email,
            subject,
        )
        return

    # Prefer Resend when configured — Railway Hobby blocks outbound SMTP (Errno 101).
    if settings.resend_api_key:
        _send_via_resend(
            subject=subject,
            to_email=to_email,
            text_body=text_body,
            html_body=html_body,
        )
        return

    if not settings.smtp_host:
        raise RuntimeError("SMTP is enabled but smtp_host is not configured")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.set_content(text_body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_starttls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    except OSError as exc:
        # Railway Hobby/Trial: outbound SMTP ports are blocked at the network layer.
        raise RuntimeError(
            "SMTP network unreachable (common on Railway Hobby). "
            "Set RESEND_API_KEY and use Resend HTTPS instead of Gmail SMTP. "
            f"Original error: {exc}"
        ) from exc

    logger.info("Email sent via SMTP to=%s subject=%s", to_email, subject)


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
