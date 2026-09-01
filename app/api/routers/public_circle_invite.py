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
from app.core.request_meta import public_api_base_url
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
    # Full logo for WhatsApp / LinkedIn link preview cards.
    return f"{_frontend_base()}/assets/zenk-logo.png"


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
    circle_name: str = "",
    leader_name: str = "",
) -> str:
    t = html.escape(title)
    d = html.escape(description)
    u = html.escape(page_url)
    img = html.escape(image_url)
    dest = html.escape(redirect_url)
    dest_js = json.dumps(redirect_url)
    circle = html.escape(circle_name or "your circle")
    leader = html.escape(leader_name or "Your circle leader")
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
  <meta property="og:image:secure_url" content="{img}" />
  <meta property="og:image:width" content="512" />
  <meta property="og:image:height" content="512" />
  <meta property="og:image:alt" content="ZenK Impact — sponsor circle invite" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{t}" />
  <meta name="twitter:description" content="{d}" />
  <meta name="twitter:image" content="{img}" />
  <link rel="icon" href="{favicon}" />
  <meta http-equiv="refresh" content="0;url={dest}" />
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
      font-family: Manrope, system-ui, sans-serif;
      background:
        radial-gradient(ellipse 80% 60% at 50% 0%, rgba(72, 183, 255, 0.18), transparent 60%),
        #f4f3eb;
      color: #191c1d;
    }}
    .card {{
      width: min(100%, 420px);
      overflow: hidden;
      text-align: center;
      background: #fff;
      border-radius: 20px;
      border: 1px solid rgba(189, 201, 193, 0.45);
      box-shadow: 0 24px 48px rgba(15, 23, 42, 0.1);
    }}
    .hero {{
      padding: 28px 24px 22px;
      background: linear-gradient(118deg, #0f5f9c 0%, #1a85d6 38%, #48b7ff 100%);
      color: #fff;
    }}
    .hero img {{
      width: 88px;
      height: auto;
      object-fit: contain;
      margin: 0 auto 14px;
      display: block;
    }}
    .hero h1 {{
      font-size: 1.2rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      margin: 0 0 8px;
      line-height: 1.3;
    }}
    .hero p {{
      margin: 0;
      font-size: 0.9rem;
      line-height: 1.55;
      color: rgba(255, 255, 255, 0.92);
    }}
    .body {{
      padding: 22px 24px 26px;
    }}
    .chip {{
      display: inline-block;
      margin-bottom: 12px;
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #1a85d6;
      background: #edf7ff;
      border: 1px solid #b8dff8;
    }}
    .steps {{
      margin: 0 0 18px;
      padding: 0;
      list-style: none;
      text-align: left;
      font-size: 13px;
      color: #64748b;
      line-height: 1.5;
    }}
    .steps li {{
      padding: 6px 0 6px 22px;
      position: relative;
    }}
    .steps li::before {{
      content: '';
      position: absolute;
      left: 0;
      top: 0.72em;
      width: 7px;
      height: 7px;
      border-radius: 999px;
      background: #48b7ff;
    }}
    .cta {{
      display: inline-block;
      padding: 12px 22px;
      border-radius: 10px;
      background: #1a85d6;
      color: #fff !important;
      font-weight: 700;
      font-size: 14px;
      text-decoration: none;
      box-shadow: 0 8px 20px rgba(26, 133, 214, 0.28);
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="hero">
      <img src="{img}" alt="ZenK Impact" width="88" height="88" />
      <h1>Join {circle}</h1>
      <p>{leader} invited you to come together for the students we support — with privacy, care, and real impact.</p>
    </div>
    <div class="body">
      <span class="chip">Circle invite</span>
      <ul class="steps">
        <li>Open the link and sign up or sign in</li>
        <li>Complete Zenk ID verification</li>
        <li>Wait for your leader to approve you</li>
      </ul>
      <p style="margin:0;"><a class="cta" href="{dest}">Continue to join</a></p>
    </div>
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
    title = f"Join {circle_name} on ZenK Impact"
    if leader:
        description = (
            f"{leader} invited you to come together for the students {circle_name} supports — "
            "private, verified, and backed by your circle on ZenK. Tap to join."
        )
    else:
        description = (
            f"Join {circle_name} on ZenK — come together for students and their betterment, "
            "with privacy and care built in. Tap to join."
        )

    page_url = f"{public_api_base_url(request)}/public/circle-invite/{raw}"

    if not _is_link_preview_bot(request.headers.get("user-agent", "")):
        return RedirectResponse(url=join, status_code=302)

    body = _og_html(
        title=title,
        description=description,
        page_url=page_url,
        image_url=_og_image_url(),
        redirect_url=join,
        circle_name=circle_name,
        leader_name=leader or "",
    )
    return HTMLResponse(content=body, status_code=200)
