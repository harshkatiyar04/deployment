from __future__ import annotations

import base64
import logging
import smtplib
from email.message import EmailMessage
from functools import partial
from pathlib import Path
from typing import Optional, Sequence, Union

import anyio
import httpx

from app.core.settings import settings
from app.services.email_templates import EMAIL_LOGO_CID, EMAIL_WATERMARK_CID


logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"

RecipientInput = Union[str, Sequence[str]]

_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "email"

_LOGO_CANDIDATES = (
    _ASSETS / "zenk-logo-full.png",
    _ASSETS / "zenk-logo-light.png",
    _ASSETS / "zenk-logo-email.png",
    _ASSETS / "zenk-logo.png",
    Path(__file__).resolve().parents[3] / "zenkimpact_FE" / "public" / "assets" / "zenk-logo.png",
)

_WATERMARK_PATH = _ASSETS / "zenk-watermark.png"


def _email_enabled() -> bool:
    return bool(settings.smtp_enabled or settings.resend_api_key)


def parse_email_recipients(to_email: RecipientInput) -> list[str]:
    """Normalize one address, comma/semicolon list, or sequence into unique recipients."""
    if isinstance(to_email, (list, tuple, set)):
        raw_parts = []
        for item in to_email:
            raw_parts.extend(str(item or "").replace(";", ",").split(","))
    else:
        raw_parts = str(to_email or "").replace(";", ",").split(",")

    seen: set[str] = set()
    out: list[str] = []
    for part in raw_parts:
        addr = part.strip()
        if not addr:
            continue
        key = addr.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(addr)
    return out


def resolve_email_logo_path() -> Optional[Path]:
    configured = (getattr(settings, "email_logo_path", None) or "").strip()
    if configured:
        path = Path(configured)
        if path.is_file():
            return path
        logger.warning("EMAIL_LOGO_PATH set but file missing: %s", configured)
    for candidate in _LOGO_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def resolve_email_watermark_path() -> Optional[Path]:
    if _WATERMARK_PATH.is_file():
        return _WATERMARK_PATH
    return None


def _html_related_target(msg: EmailMessage):
    html_part = None
    for part in msg.iter_parts():
        if part.get_content_type() == "text/html":
            html_part = part
            break
    return html_part or msg


def _attach_inline_assets(msg: EmailMessage) -> None:
    """Embed logo + watermark so Gmail does not depend on localhost URLs."""
    target = _html_related_target(msg)

    logo_path = resolve_email_logo_path()
    if logo_path is None:
        logger.warning("Email logo file not found — HTML may show a broken image")
    else:
        try:
            target.add_related(
                logo_path.read_bytes(),
                maintype="image",
                subtype="png",
                cid=EMAIL_LOGO_CID,
                filename="zenk-logo.png",
            )
        except OSError:
            logger.exception("Failed reading email logo from %s", logo_path)

    wm_path = resolve_email_watermark_path()
    if wm_path is not None:
        try:
            target.add_related(
                wm_path.read_bytes(),
                maintype="image",
                subtype="png",
                cid=EMAIL_WATERMARK_CID,
                filename="zenk-watermark.png",
            )
        except OSError:
            logger.exception("Failed reading email watermark from %s", wm_path)


def _attach_inline_logo(msg: EmailMessage) -> None:
    _attach_inline_assets(msg)


def _send_via_resend(
    *,
    subject: str,
    recipients: list[str],
    text_body: str,
    html_body: Optional[str] = None,
) -> None:
    """Send via Resend HTTPS API (Railway-safe — port 443)."""
    api_key = (settings.resend_api_key or "").strip()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")

    payload: dict = {
        "from": settings.email_from,
        "to": recipients,
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body

    logo_path = resolve_email_logo_path()
    wm_path = resolve_email_watermark_path()
    if html_body and (logo_path is not None or wm_path is not None):
        try:
            attachments = []
            if logo_path is not None:
                attachments.append(
                    {
                        "filename": "zenk-logo.png",
                        "content": base64.b64encode(logo_path.read_bytes()).decode("ascii"),
                        "content_id": EMAIL_LOGO_CID,
                    }
                )
            if wm_path is not None:
                attachments.append(
                    {
                        "filename": "zenk-watermark.png",
                        "content": base64.b64encode(wm_path.read_bytes()).decode("ascii"),
                        "content_id": EMAIL_WATERMARK_CID,
                    }
                )
            payload["attachments"] = attachments
        except OSError:
            logger.exception("Failed attaching inline images for Resend email")

    with httpx.Client(timeout=12.0) as client:
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

    logger.info("Email sent via Resend to=%s subject=%s", recipients, subject)


def _send_one_smtp(
    *,
    subject: str,
    recipient: str,
    text_body: str,
    html_body: Optional[str] = None,
) -> None:
    if not settings.smtp_host:
        raise RuntimeError("SMTP is enabled but smtp_host is not configured")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = recipient
    msg.set_content(text_body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")
        _attach_inline_logo(msg)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_starttls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    except OSError as exc:
        raise RuntimeError(
            "SMTP network unreachable (common on Railway Hobby). "
            "Set RESEND_API_KEY and use Resend HTTPS instead of Gmail SMTP. "
            f"Original error: {exc}"
        ) from exc

    logger.info("Email sent via SMTP to=%s subject=%s", [recipient], subject)


def _send_email_sync(
    *,
    subject: str,
    to_email: RecipientInput,
    text_body: str,
    html_body: Optional[str] = None,
    send_individually: bool = False,
) -> None:
    """
    Synchronous send. Prefer Resend HTTPS on Railway; fall back to SMTP locally.

    When ``send_individually`` is True (admin alerts), each recipient gets its own
    message — more reliable with Gmail multi-To and clearer delivery logs.
    """
    recipients = parse_email_recipients(to_email)
    if not recipients:
        logger.warning("Email skipped — no recipients subject=%s", subject)
        return

    if not _email_enabled():
        logger.info(
            "Email disabled (SMTP_ENABLED=false and no RESEND_API_KEY). Skipping to=%s subject=%s",
            recipients,
            subject,
        )
        return

    logger.info(
        "Sending email subject=%s recipients=%s individually=%s",
        subject,
        recipients,
        send_individually,
    )

    if settings.resend_api_key:
        if send_individually:
            errors: list[str] = []
            for recipient in recipients:
                try:
                    _send_via_resend(
                        subject=subject,
                        recipients=[recipient],
                        text_body=text_body,
                        html_body=html_body,
                    )
                except Exception as exc:
                    logger.exception("Resend failed for %s subject=%s", recipient, subject)
                    errors.append(f"{recipient}: {exc}")
            if errors:
                raise RuntimeError("Resend failed for some recipients: " + "; ".join(errors))
            return
        _send_via_resend(
            subject=subject,
            recipients=recipients,
            text_body=text_body,
            html_body=html_body,
        )
        return

    # SMTP: always send one message per recipient when multiple admins are listed.
    # Gmail often mishandles multi-To (and mail to yourself may only land in Sent).
    targets = recipients if (send_individually or len(recipients) > 1) else recipients
    errors = []
    for recipient in targets:
        try:
            _send_one_smtp(
                subject=subject,
                recipient=recipient,
                text_body=text_body,
                html_body=html_body,
            )
        except Exception as exc:
            logger.exception("SMTP failed for %s subject=%s", recipient, subject)
            errors.append(f"{recipient}: {exc}")
    if errors:
        raise RuntimeError("SMTP failed for some recipients: " + "; ".join(errors))


async def send_email(
    *,
    subject: str,
    to_email: RecipientInput,
    text_body: str,
    html_body: Optional[str] = None,
    send_individually: bool = False,
) -> None:
    """Send email with optional HTML body. `to_email` may be one address or a comma-separated list."""
    await anyio.to_thread.run_sync(
        partial(
            _send_email_sync,
            subject=subject,
            to_email=to_email,
            text_body=text_body,
            html_body=html_body,
            send_individually=send_individually,
        )
    )
