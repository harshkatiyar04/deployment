"""HttpOnly session cookies for access + refresh tokens."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Request, Response

from app.core.jwt_auth import jwt_settings

ACCESS_COOKIE = "zenk_access"
REFRESH_COOKIE = "zenk_refresh"


def _cookie_secure() -> bool:
    explicit = os.getenv("AUTH_COOKIE_SECURE", "").strip().lower()
    if explicit == "true":
        return True
    if explicit == "false":
        return False
    from app.core.settings import settings

    base = (settings.frontend_base_url or "").lower()
    return base.startswith("https://")


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = _cookie_secure()
    access_max_age = int(jwt_settings.access_token_expire_minutes) * 60
    refresh_max_age = int(jwt_settings.refresh_token_expire_days) * 86400
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=access_max_age,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=refresh_max_age,
        path="/auth",
    )


def clear_auth_cookies(response: Response) -> None:
    secure = _cookie_secure()
    for key, path in ((ACCESS_COOKIE, "/"), (REFRESH_COOKIE, "/auth")):
        response.delete_cookie(key=key, path=path, secure=secure, samesite="lax")


def read_refresh_token(request: Request, body_refresh: Optional[str] = None) -> Optional[str]:
    if body_refresh and body_refresh.strip():
        return body_refresh.strip()
    cookie = request.cookies.get(REFRESH_COOKIE)
    return cookie.strip() if cookie else None


def read_access_token(request: Request, bearer: Optional[str] = None) -> Optional[str]:
    if bearer and bearer.strip():
        return bearer.strip()
    cookie = request.cookies.get(ACCESS_COOKIE)
    return cookie.strip() if cookie else None


def access_expires_in_seconds() -> int:
    return int(jwt_settings.access_token_expire_minutes) * 60
