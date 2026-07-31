"""Public circle-invite landing — OG tags for WhatsApp / social crawlers."""

from __future__ import annotations

import html
import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import get_db
from app.models.circle_ops import CircleInviteToken
from app.models.signup import SignupRequest
from app.services.circle_invite_token import resolve_invite_token

router = APIRouter(tags=["Public invite"])

_BOT_FRAGMENTS = (
    "whatsapp",
    "facebookexternalhit",
    "facebot",
    "twitterbot",
    "linkedinbot",
    "slackbot",
    "discordbot",
    "telegrambot",
    "skypeuripreview",
    "embedly",
    "quora link preview",
    "pinterest",
    "vkshare",
)


def _is_link_preview_bot(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(frag in ua for frag in _BOT_FRAGMENTS)


def _frontend_base() -> str:
    return (settings.frontend_base_url or settings.website_url or "http://localhost:5173").rstrip(
        "/"
    )


def _join_url(token: str) -> str:
    return f"{_frontend_base()}/join/circle?invite={token}"


def _og_image_url() -> str:
    # Prefer a large square asset for WhatsApp summary cards
    return f"{_frontend_base()}/assets/zenk-favicon-512.png"


async def _leader_name_for_token(db: AsyncSession, token: str) -> Optional[str]:
    res = await db.execute(
        select(SignupRequest.full_name)
        .join(CircleInviteToken, CircleInviteToken.created_by == SignupRequest.id)
        .where(CircleInviteToken.token == token)
        .limit(1)
    )
    name = res.scalar_one_or_none()
    return (name or "").strip() or None


def _og_html(
    *,
    title: str,
    description: str,
    page_url: str,
    image_url: str,
    redirect_url: str,
) -> str:
    t = html.escape(title)
    d = html.escape(description)
    u = html.escape(page_url)
    img = html.escape(image_url)
    dest = html.escape(redirect_url)
    dest_js = json.dumps(redirect_url)
    favicon = html.escape(_frontend_base() + "/favicon.ico")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{t}</title>
  <meta name="description" content="{d}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="ZenK Impact" />
  <meta property="og:title" content="{t}" />
  <meta property="og:description" content="{d}" />
  <meta property="og:url" content="{u}" />
  <meta property="og:image" content="{img}" />
  <meta property="og:image:alt" content="ZenK Impact" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{t}" />
  <meta name="twitter:description" content="{d}" />
  <meta name="twitter:image" content="{img}" />
  <link rel="icon" href="{favicon}" />
  <meta http-equiv="refresh" content="0;url={dest}" />
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: Manrope, system-ui, sans-serif;
      background: #f4f3eb;
      color: #191c1d;
    }}
    .card {{
      max-width: 420px;
      padding: 28px 24px;
      text-align: center;
      background: #fff;
      border-radius: 16px;
      border: 1px solid #e5e7eb;
    }}
    img {{ width: 72px; height: 72px; object-fit: contain; margin-bottom: 12px; }}
    a {{ color: #1a85d6; font-weight: 700; }}
  </style>
</head>
<body>
  <div class="card">
    <img src="{img}" alt="ZenK Impact" width="72" height="72" />
    <h1 style="font-size:1.15rem;margin:0 0 8px;">{t}</h1>
    <p style="margin:0 0 16px;color:#64748b;line-height:1.45;">{d}</p>
    <p style="margin:0;"><a href="{dest}">Continue to join</a></p>
  </div>
  <script>window.location.replace({dest_js});</script>
</body>
</html>
"""


@router.get("/public/circle-invite/{token}")
async def public_circle_invite_landing(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Humans → redirect to FE join page.
    WhatsApp / social crawlers → HTML with Open Graph (ZenK logo + invite copy).
    """
    raw = (token or "").strip()
    join = _join_url(raw) if raw else _frontend_base()
    resolved = await resolve_invite_token(db, raw) if raw else None

    if not resolved:
        if _is_link_preview_bot(request.headers.get("user-agent", "")):
            body = _og_html(
                title="ZenK Impact invite",
                description="This invite link is invalid or has expired. Ask your circle leader for a new link.",
                page_url=str(request.url),
                image_url=_og_image_url(),
                redirect_url=_frontend_base() + "/join/circle",
            )
            return HTMLResponse(content=body, status_code=404)
        return RedirectResponse(url=_frontend_base() + "/join/circle", status_code=302)

    _circle_id, circle_name = resolved
    leader = await _leader_name_for_token(db, raw)
    title = f"You're invited to join {circle_name} on ZenK Impact"
    if leader:
        description = (
            f"{leader} invited you to their sponsor circle — "
            "a private group funding student welfare through ZenK. "
            "Open the link to sign up and complete Zenk ID verification."
        )
    else:
        description = (
            "You're invited to a ZenK Impact sponsor circle — "
            "a private group funding student welfare. "
            "Open the link to sign up and complete Zenk ID verification."
        )

    if not _is_link_preview_bot(request.headers.get("user-agent", "")):
        return RedirectResponse(url=join, status_code=302)

    body = _og_html(
        title=title,
        description=description,
        page_url=str(request.url),
        image_url=_og_image_url(),
        redirect_url=join,
    )
    return HTMLResponse(content=body, status_code=200)
