"""JWT token creation and validation utilities."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.env import get_env_file
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"


class JWTSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_file(), env_file_encoding="utf-8", extra="ignore"
    )
    secret_key: str = Field(default="changeme-insecure-default")
    access_token_expire_minutes: int = Field(default=15)  # OAuth-style short-lived access token
    refresh_token_expire_days: int = Field(default=7)  # Refresh token lifetime


jwt_settings = JWTSettings()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=jwt_settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, jwt_settings.secret_key, algorithm=ALGORITHM)


async def get_current_user_from_token(
    token: str, db: AsyncSession
) -> Optional[object]:
    """
    Validate a JWT token and return the SignupRequest user.
    Returns None if the token is invalid or the user is not found.
    Used directly by the WebSocket handler (not as a FastAPI Depends,
    because browser WebSocket does not support Authorization headers).
    """
    # Lazy import to avoid circular imports
    from app.models.signup import SignupRequest

    try:
        payload = jwt.decode(token, jwt_settings.secret_key, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        logger.warning("Invalid JWT token")
        return None

    result = await db.execute(select(SignupRequest).where(SignupRequest.id == user_id))
    return result.scalar_one_or_none()


from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from fastapi import Depends, HTTPException, Request, status
from app.db.session import get_db
from app.core.auth_cookies import read_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)
http_bearer_optional = HTTPBearer(auto_error=False)


async def resolve_access_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer_optional),
) -> Optional[str]:
    bearer = credentials.credentials if credentials else None
    return read_access_token(request, bearer)


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer_optional),
    db: AsyncSession = Depends(get_db),
):
    """Return user when Bearer or HttpOnly access cookie is present and valid."""
    token = read_access_token(request, credentials.credentials if credentials else None)
    if not token:
        return None
    return await get_current_user_from_token(token, db)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer_optional),
    db: AsyncSession = Depends(get_db),
):
    """FastAPI dependency — JWT from Authorization header or HttpOnly cookie."""
    token = read_access_token(request, credentials.credentials if credentials else None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_current_user_from_token(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
