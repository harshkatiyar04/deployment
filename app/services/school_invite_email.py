"""Email notifications for school portal invites."""
from __future__ import annotations

import logging

from app.core.settings import settings
from app.services.email import send_email

logger = logging.getLogger(__name__)


async def send_school_portal_invite_email(
    *,
    to_email: str,
    display_name: str,
    school_name: str,
    portal_role: str,
    join_url: str,
    expires_at_iso: str,
) -> bool:
    """
    Send invite email. Returns True if SMTP sent, False if skipped/disabled.
  """
    role_label = "Principal" if portal_role == "principal" else "School staff"
    subject = f"ZenK — Join {school_name} on the school portal"

    text_body = (
        f"Hello {display_name},\n\n"
        f"You have been invited to join {school_name} on ZenK Impact as {role_label}.\n\n"
        f"Open this link to create your account and access the school dashboard:\n"
        f"{join_url}\n\n"
        f"This link expires on {expires_at_iso}.\n\n"
        f"If you did not expect this invitation, you can ignore this email.\n\n"
        "Regards,\n"
        "ZenK Impact\n"
    )

    html_body = f"""
    <div style="font-family: system-ui, sans-serif; max-width: 560px; color: #0f172a;">
      <p>Hello <strong>{display_name}</strong>,</p>
      <p>You have been invited to join <strong>{school_name}</strong> on ZenK Impact as <strong>{role_label}</strong>.</p>
      <p><a href="{join_url}" style="display:inline-block;padding:12px 20px;background:#0f766e;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">Accept invitation</a></p>
      <p style="font-size:13px;color:#64748b;">Or copy this link:<br><a href="{join_url}">{join_url}</a></p>
      <p style="font-size:13px;color:#64748b;">Expires: {expires_at_iso}</p>
    </div>
    """

    if not settings.smtp_enabled:
        logger.info("School invite email skipped (SMTP disabled) to=%s", to_email)
        return False

    try:
        await send_email(
            subject=subject,
            to_email=to_email,
            text_body=text_body,
            html_body=html_body,
        )
        return True
    except Exception:
        logger.exception("Failed to send school invite email to=%s", to_email)
        return False
