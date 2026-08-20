"""Email template rendering — white brand header, Zenk blue/gold, mobile-safe timelines."""
from __future__ import annotations

import html

EMAIL_LOGO_CID = "zenk-logo"
EMAIL_WATERMARK_CID = "zenk-watermark"

# Brand from logo
ZENK_BLUE = "#48B7FF"
ZENK_BLUE_DEEP = "#1A85D6"
ZENK_GOLD = "#FBB017"
ZENK_ORANGE = "#C45D00"
ZENK_INK = "#1A1916"
ZENK_MUTED = "#5C574F"
ZENK_SOFT = "#8A847A"
ZENK_PAGE = "#F7F8F6"
ZENK_CARD = "#FFFFFF"
ZENK_PANEL = "#FAFAF8"
ZENK_BORDER = "#E6E9EC"
ZENK_SUCCESS = "#059669"


def _esc(value: str | None) -> str:
    return html.escape(value or "", quote=True)


def _site_base(website_url: str) -> str:
    """Public site base for email CTAs — never emit localhost links."""
    base = (website_url or "https://in.zenkimpact.com").rstrip("/")
    lowered = base.lower()
    if "localhost" in lowered or "127.0.0.1" in lowered:
        return "https://in.zenkimpact.com"
    return base


def _logo_src(*, logo_url: str | None = None) -> str:
    if logo_url and logo_url.strip():
        return logo_url.strip()
    return f"cid:{EMAIL_LOGO_CID}"


def _wm_src() -> str:
    return f"cid:{EMAIL_WATERMARK_CID}"


def _brand_header(*, logo_url: str | None = None) -> str:
    """White header — full official logo asset only (mark + ZENK + 絆 + tagline)."""
    logo = _logo_src(logo_url=logo_url)
    return f"""
              <img class="zenk-logo" src="{logo}" alt="ZenK Impact — Building one impact at a time"
                width="220" height="54"
                style="display:block;max-width:220px;width:220px;height:auto;border:0;outline:none;margin:0 auto 14px auto;object-fit:contain;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin:0 auto;">
                <tr>
                  <td width="40" height="2" style="width:40px;height:2px;background-color:{ZENK_BLUE};font-size:0;line-height:0;">&nbsp;</td>
                  <td width="10" height="2" style="width:10px;height:2px;background-color:{ZENK_GOLD};font-size:0;line-height:0;">&nbsp;</td>
                  <td width="8" height="2" style="width:8px;height:2px;background-color:{ZENK_ORANGE};font-size:0;line-height:0;">&nbsp;</td>
                </tr>
              </table>
"""


def _shell(
    *,
    title: str,
    header_inner: str,
    body_inner: str,
    footer_note: str,
) -> str:
    """White brand shell — compact assets, no overflow clip on logo, mobile-safe."""
    wm = _wm_src()
    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light only">
  <meta name="supported-color-schemes" content="light">
  <title>{_esc(title)}</title>
  <!--[if mso]>
  <style type="text/css">body, table, td {{ font-family: Arial, sans-serif !important; }}</style>
  <![endif]-->
  <style type="text/css">
    :root {{ color-scheme: light only; }}
    body {{ margin:0 !important; padding:0 !important; width:100% !important; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
    img {{ border:0; outline:none; text-decoration:none; -ms-interpolation-mode:bicubic; }}
    table {{ border-collapse:collapse; }}
    .zenk-outer {{ width:100% !important; }}
    .zenk-card {{ width:100% !important; max-width:600px !important; }}
    @media only screen and (max-width: 620px) {{
      .zenk-pad {{ padding-left:18px !important; padding-right:18px !important; }}
      .zenk-pad-lg {{ padding:22px 18px 14px 18px !important; }}
      .zenk-title {{ font-size:22px !important; line-height:1.3 !important; }}
      .zenk-logo {{ width:170px !important; max-width:170px !important; height:auto !important; }}
      .zenk-cta {{ display:block !important; width:100% !important; box-sizing:border-box !important; text-align:center !important; }}
      .zenk-outer-pad {{ padding:18px 10px !important; }}
      .zenk-wm {{ width:64px !important; height:auto !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:{ZENK_PAGE};font-family:Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased;">
  <div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">Zenk Impact · {_esc(title)}</div>
  <table role="presentation" class="zenk-outer" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color:{ZENK_PAGE};width:100%;">
    <tr>
      <td align="center" class="zenk-outer-pad" style="padding:28px 12px;">
        <table role="presentation" class="zenk-card" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width:600px;width:100%;background-color:{ZENK_CARD};border-radius:16px;border:1px solid {ZENK_BORDER};">
          <tr>
            <td align="center" class="zenk-pad-lg" style="padding:26px 24px 16px 24px;background-color:#ffffff;border-radius:16px 16px 0 0;border-bottom:1px solid {ZENK_BORDER};">
              {header_inner}
            </td>
          </tr>
          {body_inner}
          <tr>
            <td align="center" class="zenk-pad" style="padding:6px 24px 4px 24px;">
              <img class="zenk-wm" src="{wm}" alt="" width="72"
                style="display:block;max-width:72px;width:72px;height:auto;border:0;margin:0 auto;opacity:0.4;">
            </td>
          </tr>
          <tr>
            <td class="zenk-pad" style="padding:10px 24px 22px 24px;background-color:{ZENK_PANEL};border-radius:0 0 16px 16px;border-top:1px solid rgba(26,25,22,0.06);text-align:center;">
              <p style="margin:0 0 4px 0;font-size:13px;font-weight:700;color:{ZENK_INK};">
                <span style="color:{ZENK_BLUE};">ZEN</span><span style="color:{ZENK_GOLD};">K</span> Impact
              </p>
              <p style="margin:0;font-size:12px;line-height:1.5;color:{ZENK_SOFT};">{_esc(footer_note)}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _timeline_html(steps: list[dict]) -> str:
    """
    Classic simple ticker (older style): solid discs + check / number.
    Avoid bordered rings — Gmail often renders those as cropped squares.
    """
    rows: list[str] = []
    for i, step in enumerate(steps):
        state = (step.get("state") or "upcoming").lower()
        if state == "done":
            mark, mark_bg, label_color, hint_color = "&#10003;", "#059669", ZENK_INK, "#059669"
        elif state == "active":
            mark, mark_bg, label_color, hint_color = str(i + 1), ZENK_BLUE_DEEP, ZENK_INK, ZENK_BLUE_DEEP
        elif state == "issue":
            mark, mark_bg, label_color, hint_color = "!", "#C2410C", ZENK_INK, "#C2410C"
        else:
            mark, mark_bg, label_color, hint_color = str(i + 1), "#D6D1C7", ZENK_SOFT, ZENK_SOFT

        border = "border-bottom:1px solid rgba(26,25,22,0.08);" if i < len(steps) - 1 else ""
        rows.append(
            f"""
                <tr>
                  <td style="padding:12px 14px;{border}">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                      <tr>
                        <td width="36" valign="top" style="width:36px;">
                          <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                            <tr>
                              <td align="center" width="28" height="28"
                                style="width:28px;height:28px;background-color:{mark_bg};border-radius:14px;color:#ffffff;font-size:13px;font-weight:700;line-height:28px;">
                                {mark}
                              </td>
                            </tr>
                          </table>
                        </td>
                        <td valign="middle" style="padding-left:10px;">
                          <p style="margin:0 0 2px 0;font-size:14px;font-weight:700;color:{label_color};">{_esc(step.get("label"))}</p>
                          <p style="margin:0;font-size:12px;color:{hint_color};">{_esc(step.get("hint"))}</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>"""
        )
    return f"""
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"
                style="background-color:{ZENK_PANEL};border:1px solid rgba(26,25,22,0.08);border-radius:12px;">
                {''.join(rows)}
              </table>"""


def _cta(url: str, label: str, *, color: str = ZENK_BLUE_DEEP) -> str:
    return (
        f'<a class="zenk-cta" href="{_esc(url)}" style="display:inline-block;padding:14px 28px;'
        f"background-color:{color};color:#ffffff;text-decoration:none;border-radius:12px;"
        f'font-weight:700;font-size:15px;min-width:180px;">{_esc(label)}</a>'
    )


def _note_box(title: str, note: str) -> str:
    if not (note or "").strip():
        return ""
    return f"""
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"
                style="background-color:#FFFBEB;border:1px solid #FDE68A;border-radius:12px;margin:0 0 18px 0;">
                <tr>
                  <td style="padding:14px 16px;border-left:4px solid {ZENK_GOLD};">
                    <p style="margin:0 0 6px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#B45309;">{_esc(title)}</p>
                    <p style="margin:0;font-size:14px;line-height:1.55;color:{ZENK_INK};">{_esc(note)}</p>
                  </td>
                </tr>
              </table>"""


def render_admin_notification_html(
    *,
    persona_label: str,
    signup_id: str,
    full_name: str,
    email: str,
    mobile: str,
    kyc_status: str,
    website_url: str,
    logo_url: str | None = None,
) -> str:
    admin_url = f"{_site_base(website_url)}/admin/kyc"
    status = (kyc_status or "pending").replace("_", " ").title()
    header = _brand_header(logo_url=logo_url)
    body = f"""
          <tr>
            <td class="zenk-pad" style="padding:28px 28px 8px 28px;">
              <p style="margin:0 0 10px 0;font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{ZENK_BLUE_DEEP};">New registration</p>
              <h1 class="zenk-title" style="margin:0 0 14px 0;font-size:24px;line-height:1.3;color:{ZENK_INK};font-weight:700;">A {_esc(persona_label)} needs KYC review</h1>
              <p style="margin:0 0 8px 0;font-size:15px;line-height:1.6;color:{ZENK_MUTED};">Hello Admin,</p>
              <p style="margin:0 0 20px 0;font-size:15px;line-height:1.6;color:{ZENK_MUTED};">
                <strong style="color:{ZENK_INK};">{_esc(full_name)}</strong> just registered as a
                <strong style="color:{ZENK_INK};">{_esc(persona_label)}</strong>. Documents are waiting in the admin console.
              </p>
            </td>
          </tr>
          <tr>
            <td class="zenk-pad" style="padding:0 28px 20px 28px;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color:{ZENK_PANEL};border:1px solid rgba(26,25,22,0.08);border-radius:12px;">
                <tr><td style="padding:12px 16px;border-bottom:1px solid rgba(26,25,22,0.07);"><p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{ZENK_SOFT};">Signup ID</p><p style="margin:0;font-size:14px;color:{ZENK_INK};word-break:break-all;">{_esc(signup_id)}</p></td></tr>
                <tr><td style="padding:12px 16px;border-bottom:1px solid rgba(26,25,22,0.07);"><p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{ZENK_SOFT};">Name</p><p style="margin:0;font-size:14px;color:{ZENK_INK};">{_esc(full_name)}</p></td></tr>
                <tr><td style="padding:12px 16px;border-bottom:1px solid rgba(26,25,22,0.07);"><p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{ZENK_SOFT};">Email</p><p style="margin:0;font-size:14px;color:{ZENK_INK};">{_esc(email)}</p></td></tr>
                <tr><td style="padding:12px 16px;border-bottom:1px solid rgba(26,25,22,0.07);"><p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{ZENK_SOFT};">Mobile</p><p style="margin:0;font-size:14px;color:{ZENK_INK};">{_esc(mobile)}</p></td></tr>
                <tr><td style="padding:12px 16px;"><p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{ZENK_SOFT};">Status</p><p style="margin:0;font-size:14px;font-weight:700;color:#B45309;">{_esc(status)}</p></td></tr>
              </table>
            </td>
          </tr>
          <tr>
            <td align="center" class="zenk-pad" style="padding:4px 28px 24px 28px;">
              {_cta(admin_url, "Review KYC documents")}
            </td>
          </tr>
"""
    return _shell(
        title="Zenk — new registration",
        header_inner=header,
        body_inner=body,
        footer_note="Automated admin alert · please do not reply",
    )


def render_user_approval_html(
    *,
    full_name: str,
    persona_label: str,
    website_url: str,
    logo_url: str | None = None,
    flow: str = "standard",
    circle_name: str | None = None,
    review_note: str | None = None,
) -> str:
    login_url = f"{_site_base(website_url)}/login"
    first = _esc((full_name or "").strip().split(" ")[0] or "there")
    header = _brand_header(logo_url=logo_url)
    circle = circle_name or "your circle"

    if flow == "member_awaiting_leader":
        kicker = "Identity verified"
        title = f"Almost there, {first}"
        lede = (
            f"Zenk verified your <strong style=\"color:{ZENK_INK};\">{_esc(persona_label)}</strong> registration. "
            f"Your circle leader still needs to approve you for <strong style=\"color:{ZENK_INK};\">{_esc(circle)}</strong>."
        )
        steps = [
            {"label": "Applied", "hint": "Request received", "state": "done"},
            {"label": "Zenk verified", "hint": "Identity cleared", "state": "done"},
            {"label": "Leader approval", "hint": f"Waiting on {circle}", "state": "active"},
            {"label": "Dashboard", "hint": "Full circle access", "state": "upcoming"},
        ]
        cta_label = "Check membership status"
        footer = "We'll email you again when your leader decides"
        kicker_color = ZENK_BLUE_DEEP
    else:
        kicker = "Application approved"
        title = f"You're in, {first}"
        lede = (
            f"Your <strong style=\"color:{ZENK_INK};\">{_esc(persona_label)}</strong> registration on Zenk has been verified. "
            "Sign in with the email and password you used at signup."
        )
        steps = [
            {"label": "Submitted", "hint": "Application received", "state": "done"},
            {"label": "Verified", "hint": "KYC approved", "state": "done"},
            {"label": "Ready", "hint": "Sign in to continue", "state": "active"},
        ]
        cta_label = "Sign in to Zenk"
        footer = "Welcome aboard · this inbox is not monitored for replies"
        kicker_color = ZENK_BLUE_DEEP

    body = f"""
          <tr>
            <td class="zenk-pad" style="padding:28px 28px 8px 28px;text-align:center;">
              <p style="margin:0 0 14px 0;font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{kicker_color};">{kicker}</p>
              <h1 class="zenk-title" style="margin:0 0 12px 0;font-size:26px;line-height:1.25;color:{ZENK_INK};font-weight:700;">{title}</h1>
              <p style="margin:0 0 20px 0;font-size:15px;line-height:1.65;color:{ZENK_MUTED};">{lede}</p>
            </td>
          </tr>
          <tr>
            <td class="zenk-pad" style="padding:0 28px 18px 28px;">
              <p style="margin:0 0 10px 0;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{ZENK_SOFT};text-align:center;">Your progress</p>
              {_timeline_html(steps)}
            </td>
          </tr>
          <tr>
            <td align="center" class="zenk-pad" style="padding:4px 28px 20px 28px;">
              {_cta(login_url, cta_label)}
            </td>
          </tr>
"""
    return _shell(
        title="KYC Approved — Zenk",
        header_inner=header,
        body_inner=body,
        footer_note=footer,
    )


def render_user_info_required_html(
    *,
    full_name: str,
    persona_label: str,
    review_note: str,
    website_url: str,
    logo_url: str | None = None,
) -> str:
    login_url = f"{_site_base(website_url)}/login"
    first = _esc((full_name or "").strip().split(" ")[0] or "there")
    header = _brand_header(logo_url=logo_url)
    steps = [
        {"label": "Submitted", "hint": "Application received", "state": "done"},
        {"label": "Review", "hint": "More documents needed", "state": "active"},
        {"label": "Verified", "hint": "After you resubmit", "state": "upcoming"},
    ]
    body = f"""
          <tr>
            <td class="zenk-pad" style="padding:28px 28px 8px 28px;text-align:center;">
              <p style="margin:0 0 12px 0;font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#B45309;">Action needed</p>
              <h1 class="zenk-title" style="margin:0 0 12px 0;font-size:24px;line-height:1.3;color:{ZENK_INK};font-weight:700;">We need a little more, {first}</h1>
              <p style="margin:0 0 16px 0;font-size:15px;line-height:1.65;color:{ZENK_MUTED};">
                To finish verifying your <strong style="color:{ZENK_INK};">{_esc(persona_label)}</strong> registration,
                please upload what our team asked for below.
              </p>
              {_note_box("What we need", review_note)}
            </td>
          </tr>
          <tr>
            <td class="zenk-pad" style="padding:0 28px 18px 28px;">
              <p style="margin:0 0 10px 0;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{ZENK_SOFT};text-align:center;">Your progress</p>
              {_timeline_html(steps)}
            </td>
          </tr>
          <tr>
            <td align="center" class="zenk-pad" style="padding:4px 28px 20px 28px;">
              {_cta(login_url, "Sign in and upload documents", color="#C2410C")}
            </td>
          </tr>
"""
    return _shell(
        title="Additional information required — Zenk",
        header_inner=header,
        body_inner=body,
        footer_note="Reply isn't monitored · sign in to upload documents",
    )


def render_user_rejected_html(
    *,
    full_name: str,
    persona_label: str,
    review_note: str,
    website_url: str,
    logo_url: str | None = None,
) -> str:
    login_url = f"{_site_base(website_url)}/login"
    first = _esc((full_name or "").strip().split(" ")[0] or "there")
    header = _brand_header(logo_url=logo_url)
    steps = [
        {"label": "Submitted", "hint": "Application received", "state": "done"},
        {"label": "Review complete", "hint": "Not approved this time", "state": "issue"},
        {"label": "Next step", "hint": "Contact support if needed", "state": "upcoming"},
    ]
    body = f"""
          <tr>
            <td class="zenk-pad" style="padding:28px 28px 8px 28px;text-align:center;">
              <p style="margin:0 0 12px 0;font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#B45309;">Application update</p>
              <h1 class="zenk-title" style="margin:0 0 12px 0;font-size:24px;line-height:1.3;color:{ZENK_INK};font-weight:700;">Hi {first}, we have an update</h1>
              <p style="margin:0 0 16px 0;font-size:15px;line-height:1.65;color:{ZENK_MUTED};">
                Your <strong style="color:{ZENK_INK};">{_esc(persona_label)}</strong> registration was not approved at this time.
              </p>
              {_note_box("Note from our team", review_note)}
            </td>
          </tr>
          <tr>
            <td class="zenk-pad" style="padding:0 28px 18px 28px;">
              <p style="margin:0 0 10px 0;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{ZENK_SOFT};text-align:center;">Your progress</p>
              {_timeline_html(steps)}
            </td>
          </tr>
          <tr>
            <td align="center" class="zenk-pad" style="padding:4px 28px 20px 28px;">
              {_cta(login_url, "Sign in for details")}
            </td>
          </tr>
"""
    return _shell(
        title="Application update — Zenk",
        header_inner=header,
        body_inner=body,
        footer_note="Questions? Reach Zenk support from the website",
    )


def render_member_circle_decision_html(
    *,
    full_name: str,
    persona_label: str,
    circle_name: str,
    approved: bool,
    website_url: str,
    logo_url: str | None = None,
) -> str:
    login_url = f"{_site_base(website_url)}/login"
    first = _esc((full_name or "").strip().split(" ")[0] or "there")
    header = _brand_header(logo_url=logo_url)
    circle = circle_name or "your circle"

    if approved:
        kicker, kicker_color = "Welcome to the circle", ZENK_BLUE_DEEP
        title = f"You're in, {first}"
        lede = (
            f"Your circle leader approved your <strong style=\"color:{ZENK_INK};\">{_esc(persona_label)}</strong> "
            f"membership in <strong style=\"color:{ZENK_INK};\">{_esc(circle)}</strong>. The dashboard is open."
        )
        steps = [
            {"label": "Applied", "hint": "Request sent", "state": "done"},
            {"label": "Zenk verified", "hint": "Identity cleared", "state": "done"},
            {"label": "Leader approved", "hint": circle, "state": "done"},
            {"label": "Dashboard", "hint": "Ready now", "state": "active"},
        ]
        cta = _cta(login_url, "Open your circle")
        footer = "Welcome aboard"
    else:
        kicker, kicker_color = "Membership update", "#B45309"
        title = f"Hi {first}"
        lede = (
            f"Your request to join <strong style=\"color:{ZENK_INK};\">{_esc(circle)}</strong> was not accepted "
            "by the circle leader. Reach your leader or Zenk support if you need a next step."
        )
        steps = [
            {"label": "Applied", "hint": "Request sent", "state": "done"},
            {"label": "Zenk verified", "hint": "Identity cleared", "state": "done"},
            {"label": "Leader decision", "hint": "Not accepted", "state": "issue"},
            {"label": "Dashboard", "hint": "Closed for now", "state": "upcoming"},
        ]
        cta = _cta(login_url, "Sign in for details")
        footer = "You can apply again with another invite if invited"

    body = f"""
          <tr>
            <td class="zenk-pad" style="padding:28px 28px 8px 28px;text-align:center;">
              <p style="margin:0 0 12px 0;font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{kicker_color};">{kicker}</p>
              <h1 class="zenk-title" style="margin:0 0 12px 0;font-size:26px;line-height:1.25;color:{ZENK_INK};font-weight:700;">{title}</h1>
              <p style="margin:0 0 20px 0;font-size:15px;line-height:1.65;color:{ZENK_MUTED};">{lede}</p>
            </td>
          </tr>
          <tr>
            <td class="zenk-pad" style="padding:0 28px 18px 28px;">
              <p style="margin:0 0 10px 0;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{ZENK_SOFT};text-align:center;">Membership progress</p>
              {_timeline_html(steps)}
            </td>
          </tr>
          <tr>
            <td align="center" class="zenk-pad" style="padding:4px 28px 20px 28px;">
              {cta}
            </td>
          </tr>
"""
    return _shell(
        title=f"{'Welcome' if approved else 'Update'} — {circle}",
        header_inner=header,
        body_inner=body,
        footer_note=footer,
    )


def render_leader_member_ready_html(
    *,
    member_name: str,
    member_email: str,
    circle_name: str,
    website_url: str,
    logo_url: str | None = None,
) -> str:
    """
    Premium Leader Action transactional email (polish pass).
    Business data/links unchanged.
    """
    login_url = f"{_site_base(website_url)}/login"
    logo = _logo_src(logo_url=logo_url)
    name = _esc(member_name)
    email = _esc(member_email)
    circle = _esc(circle_name)

    journey = f"""
              <table role="presentation" class="zenk-journey-track" cellspacing="0" cellpadding="0" border="0" width="100%" style="width:100%;margin:0 0 6px 0;">
                <tr>
                  <td class="zenk-node" width="48" align="center" valign="middle" style="width:48px;">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
                      <tr>
                        <td align="center" width="30" height="30" style="width:30px;height:30px;background-color:{ZENK_SUCCESS};border-radius:15px;color:#ffffff;font-size:14px;font-weight:700;line-height:30px;">&#10003;</td>
                      </tr>
                    </table>
                  </td>
                  <td class="zenk-rail" valign="middle" style="border-top:1px solid {ZENK_SUCCESS};font-size:0;line-height:0;height:1px;">&nbsp;</td>
                  <td class="zenk-node" width="48" align="center" valign="middle" style="width:48px;">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
                      <tr>
                        <td align="center" width="30" height="30" style="width:30px;height:30px;background-color:{ZENK_SUCCESS};border-radius:15px;color:#ffffff;font-size:14px;font-weight:700;line-height:30px;">&#10003;</td>
                      </tr>
                    </table>
                  </td>
                  <td class="zenk-rail" valign="middle" style="border-top:1px solid {ZENK_SUCCESS};font-size:0;line-height:0;height:1px;">&nbsp;</td>
                  <td class="zenk-node" width="48" align="center" valign="middle" style="width:48px;">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
                      <tr>
                        <td align="center" width="30" height="30" style="width:30px;height:30px;background-color:{ZENK_BLUE};border-radius:15px;color:#ffffff;font-size:13px;font-weight:800;line-height:30px;">03</td>
                      </tr>
                    </table>
                  </td>
                  <td class="zenk-rail" valign="middle" style="border-top:1px solid #D0D5DA;font-size:0;line-height:0;height:1px;">&nbsp;</td>
                  <td class="zenk-node" width="48" align="center" valign="middle" style="width:48px;">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
                      <tr>
                        <td align="center" width="30" height="30" style="width:30px;height:30px;background-color:#ffffff;border:2px solid #D0D5DA;border-radius:15px;color:{ZENK_SOFT};font-size:12px;font-weight:700;line-height:26px;">04</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              <table role="presentation" class="zenk-journey" cellspacing="0" cellpadding="0" border="0" width="100%" style="width:100%;">
                <tr>
                  <td class="zenk-step" width="25%" valign="top" align="center" style="width:25%;padding:12px 10px 4px 10px;">
                    <p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{ZENK_SOFT};">01</p>
                    <p style="margin:0 0 4px 0;font-size:14px;font-weight:700;color:{ZENK_INK};">Applied</p>
                    <p style="margin:0;font-size:12px;line-height:1.4;color:{ZENK_SUCCESS};">Complete</p>
                  </td>
                  <td class="zenk-step" width="25%" valign="top" align="center" style="width:25%;padding:12px 10px 4px 10px;">
                    <p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{ZENK_SOFT};">02</p>
                    <p style="margin:0 0 4px 0;font-size:14px;font-weight:700;color:{ZENK_INK};">Verified</p>
                    <p style="margin:0;font-size:12px;line-height:1.4;color:{ZENK_SUCCESS};">Identity cleared</p>
                  </td>
                  <td class="zenk-step zenk-step-active" width="25%" valign="top" align="center" style="width:25%;padding:8px 6px 4px 6px;">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color:rgba(72,183,255,0.08);border:1px solid {ZENK_BLUE};border-radius:10px;">
                      <tr>
                        <td align="center" style="padding:10px 8px;">
                          <p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{ZENK_BLUE};">03</p>
                          <p style="margin:0 0 4px 0;font-size:14px;font-weight:700;color:{ZENK_INK};">Your approval</p>
                          <p style="margin:0;font-size:12px;line-height:1.4;color:{ZENK_BLUE};">Action needed</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <td class="zenk-step" width="25%" valign="top" align="center" style="width:25%;padding:12px 10px 4px 10px;">
                    <p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{ZENK_SOFT};">04</p>
                    <p style="margin:0 0 4px 0;font-size:14px;font-weight:700;color:{ZENK_SOFT};">In the circle</p>
                    <p style="margin:0;font-size:12px;line-height:1.4;color:{ZENK_SOFT};">After you approve</p>
                  </td>
                </tr>
              </table>"""

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light only">
  <meta name="supported-color-schemes" content="light">
  <title>A member is ready for your approval</title>
  <!--[if mso]>
  <style type="text/css">body, table, td {{ font-family: Arial, Helvetica, sans-serif !important; }}</style>
  <![endif]-->
  <style type="text/css">
    :root {{ color-scheme: light only; }}
    body {{ margin:0 !important; padding:0 !important; width:100% !important; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
    img {{ border:0; outline:none; text-decoration:none; -ms-interpolation-mode:bicubic; }}
    table {{ border-collapse:collapse; }}
    a {{ color:{ZENK_BLUE}; }}
    @media only screen and (max-width: 620px) {{
      .zenk-outer-pad {{ padding:16px 16px !important; }}
      .zenk-card {{ width:100% !important; }}
      .zenk-pad {{ padding-left:20px !important; padding-right:20px !important; }}
      .zenk-pad-lg {{ padding:24px 20px 18px 20px !important; }}
      .zenk-logo {{ width:190px !important; max-width:190px !important; height:auto !important; }}
      .zenk-title {{ font-size:24px !important; line-height:1.28 !important; }}
      .zenk-cta {{ display:block !important; width:100% !important; box-sizing:border-box !important; text-align:center !important; }}
      .zenk-info-col {{ display:block !important; width:100% !important; padding:0 0 14px 0 !important; border:0 !important; }}
      .zenk-journey-track {{ display:none !important; max-height:0 !important; overflow:hidden !important; mso-hide:all; }}
      .zenk-step {{ display:block !important; width:100% !important; max-width:100% !important; padding:10px 0 !important; text-align:left !important; border-left:3px solid #D0D5DA !important; padding-left:14px !important; margin:0 0 4px 0 !important; }}
      .zenk-step-active {{ border-left-color:{ZENK_BLUE} !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:{ZENK_PAGE};font-family:Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased;">
  <div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">
    {_esc(member_name)} passed ZenK verification and is waiting for your approval to join {_esc(circle_name)}.
  </div>
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color:{ZENK_PAGE};width:100%;">
    <tr>
      <td align="center" class="zenk-outer-pad" style="padding:32px 20px;">
        <table role="presentation" class="zenk-card" cellspacing="0" cellpadding="0" border="0" width="640" style="max-width:640px;width:100%;background-color:{ZENK_CARD};border:1px solid {ZENK_BORDER};border-radius:14px;">

          <tr>
            <td align="center" class="zenk-pad-lg" style="padding:32px 40px 22px 40px;background-color:#ffffff;border-radius:14px 14px 0 0;">
              <img class="zenk-logo" src="{logo}" alt="ZenK Impact — Building one impact at a time"
                width="280" height="69"
                style="display:block;max-width:280px;width:280px;height:auto;border:0;outline:none;margin:0 auto 16px auto;object-fit:contain;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
                <tr>
                  <td width="48" height="2" style="width:48px;height:2px;background-color:{ZENK_BLUE};font-size:0;line-height:0;">&nbsp;</td>
                  <td width="10" height="2" style="width:10px;height:2px;background-color:{ZENK_GOLD};font-size:0;line-height:0;">&nbsp;</td>
                  <td width="8" height="2" style="width:8px;height:2px;background-color:{ZENK_ORANGE};font-size:0;line-height:0;">&nbsp;</td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td class="zenk-pad" style="padding:12px 40px 0 40px;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td width="8" height="8" style="width:8px;height:8px;background-color:{ZENK_BLUE};border-radius:4px;font-size:0;line-height:0;">&nbsp;</td>
                  <td style="padding-left:8px;">
                    <p style="margin:0;font-size:11px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:{ZENK_BLUE};">Leader action</p>
                  </td>
                </tr>
              </table>
              <h1 class="zenk-title" style="margin:16px 0 14px 0;font-size:28px;line-height:1.25;color:{ZENK_INK};font-weight:700;">
                A member is ready<br>for your approval.
              </h1>
              <p style="margin:0 0 26px 0;font-size:15px;line-height:1.65;color:{ZENK_MUTED};">
                <strong style="color:{ZENK_INK};">{name}</strong>
                (<a href="mailto:{email}" style="color:{ZENK_BLUE};text-decoration:none;">{email}</a>)
                passed ZenK verification and is waiting to join
                <strong style="color:{ZENK_INK};">{circle}</strong>.
              </p>
            </td>
          </tr>

          <tr>
            <td class="zenk-pad" style="padding:0 40px 26px 40px;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="width:100%;border:1px solid {ZENK_BORDER};border-radius:12px;">
                <tr>
                  <td class="zenk-info-col" width="50%" valign="top" style="width:50%;padding:18px 20px 16px 20px;">
                    <p style="margin:0 0 6px 0;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{ZENK_SOFT};">Member</p>
                    <p style="margin:0;font-size:16px;font-weight:700;line-height:1.35;color:{ZENK_INK};">{name}</p>
                  </td>
                  <td class="zenk-info-col" width="50%" valign="top" style="width:50%;padding:18px 20px 16px 20px;border-left:1px solid {ZENK_BORDER};">
                    <p style="margin:0 0 6px 0;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{ZENK_SOFT};">Circle</p>
                    <p style="margin:0;font-size:16px;font-weight:700;line-height:1.35;color:{ZENK_INK};">{circle}</p>
                  </td>
                </tr>
                <tr>
                  <td colspan="2" style="padding:14px 20px 16px 20px;border-top:1px solid {ZENK_BORDER};">
                    <p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{ZENK_SOFT};">Status</p>
                    <p style="margin:0;font-size:14px;font-weight:600;color:{ZENK_BLUE};">Verified · Awaiting your approval</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td class="zenk-pad" style="padding:0 36px 10px 36px;">
              <p style="margin:0 0 16px 0;font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{ZENK_SOFT};text-align:center;">Membership journey</p>
              {journey}
            </td>
          </tr>

          <tr>
            <td align="center" class="zenk-pad" style="padding:24px 40px 8px 40px;">
              <a class="zenk-cta" href="{_esc(login_url)}"
                style="display:inline-block;padding:15px 40px;min-width:240px;background-color:{ZENK_BLUE};color:#ffffff;text-decoration:none;border-radius:10px;font-weight:700;font-size:15px;line-height:1.2;text-align:center;">
                Review pending members &#8594;
              </a>
            </td>
          </tr>
          <tr>
            <td align="center" class="zenk-pad" style="padding:8px 40px 6px 40px;">
              <a href="{_esc(login_url)}" style="font-size:13px;color:{ZENK_BLUE};text-decoration:none;">Open ZenK</a>
            </td>
          </tr>
          <tr>
            <td align="center" class="zenk-pad" style="padding:12px 40px 28px 40px;">
              <p style="margin:0;font-size:13px;line-height:1.55;color:{ZENK_SOFT};">
                One approval brings one more person into the circle.
              </p>
            </td>
          </tr>

          <tr>
            <td class="zenk-pad" style="padding:20px 40px 26px 40px;background-color:{ZENK_PANEL};border-top:1px solid {ZENK_BORDER};border-radius:0 0 14px 14px;text-align:center;">
              <p style="margin:0 0 4px 0;font-size:13px;font-weight:700;color:{ZENK_INK};">
                <span style="color:{ZENK_BLUE};">ZEN</span><span style="color:{ZENK_GOLD};">K</span> Impact
              </p>
              <p style="margin:0 0 12px 0;font-size:12px;color:{ZENK_SOFT};">Building one impact at a time</p>
              <p style="margin:0;font-size:11px;line-height:1.5;color:{ZENK_SOFT};">Only circle leaders receive this alert.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
