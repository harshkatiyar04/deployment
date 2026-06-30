"""HttpOnly admin session cookie (platform admin UI — not persona JWT)."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request, Response
from jose import JWTError, jwt

from app.core.jwt_auth import ALGORITHM, jwt_settings

ADMIN_SESSION_COOKIE = "zenk_admin_session"
ADMIN_SCOPE = "platform_admin"
ADMIN_SESSION_HOURS = 8


def _cookie_secure() -> bool:
    explicit = os.getenv("AUTH_COOKIE_SECURE", "").strip().lower()
    if explicit == "true":
        return True
    if explicit == "false":
        return False
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
        return True
    from app.core.settings import settings

    base = (settings.frontend_base_url or "").lower()
    return base.startswith("https://")


def _cookie_samesite() -> str:
    return "none" if _cookie_secure() else "lax"


def create_admin_session_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ADMIN_SESSION_HOURS)
    return jwt.encode(
        {"sub": "platform_admin", "scope": ADMIN_SCOPE, "exp": expire},
        jwt_settings.secret_key,
        algorithm=ALGORITHM,
    )


def set_admin_session_cookie(response: Response) -> None:
    secure = _cookie_secure()
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=create_admin_session_token(),
        httponly=True,
        secure=secure,
        samesite=_cookie_samesite(),
        max_age=ADMIN_SESSION_HOURS * 3600,
        path="/",
    )


def clear_admin_session_cookie(response: Response) -> None:
    secure = _cookie_secure()
    samesite = _cookie_samesite()
    response.delete_cookie(
        key=ADMIN_SESSION_COOKIE,
        path="/",
        secure=secure,
        samesite=samesite,
    )


def admin_session_valid(request: Request) -> bool:
    token = request.cookies.get(ADMIN_SESSION_COOKIE)
    if not token or not token.strip():
        return False
    try:
        payload = jwt.decode(token, jwt_settings.secret_key, algorithms=[ALGORITHM])
        return payload.get("scope") == ADMIN_SCOPE
    except JWTError:
        return False


def verify_admin_login(email: str, password: str) -> bool:
    from app.core.settings import settings

    expected_email = (settings.admin_email or "admin@zenk").strip().lower()
    provided_email = (email or "").strip().lower()
    if not secrets.compare_digest(provided_email, expected_email):
        return False

    expected_password = (settings.admin_password or "").strip()
    if not expected_password:
        if settings.admin_allow_open_dev:
            return True
        return False
    return secrets.compare_digest(password or "", expected_password)
