from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.env import get_env_file

# libpq query keys that asyncpg rejects as connect() kwargs (e.g. sslmode=require).
_ASYNCPG_DROP_QUERY_KEYS = frozenset(
    {
        "sslmode",
        "sslcert",
        "sslkey",
        "sslrootcert",
        "sslcrl",
        "channel_binding",
        "gssencmode",
        "options",
    }
)


def normalize_asyncpg_database_url(url: str) -> str:
    """Convert to postgresql+asyncpg:// and strip libpq-only query params."""
    raw = (url or "").strip()
    if not raw:
        return raw
    if raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]
    elif raw.startswith("postgres://"):
        raw = "postgresql+asyncpg://" + raw[len("postgres://") :]

    parsed = urlparse(raw)
    if not parsed.query:
        return raw
    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in _ASYNCPG_DROP_QUERY_KEYS]
    return urlunparse(parsed._replace(query=urlencode(kept)))


class DbSettings(BaseSettings):
    """
    DB config lives under app/db as requested.
    You can override any of these using environment variables.
    """

    # NOTE: We share one `.env` across multiple settings classes (DB + SMTP + app).
    # DbSettings should ignore keys it doesn't define.
    model_config = SettingsConfigDict(env_file=get_env_file(), env_file_encoding="utf-8", extra="ignore")

    database_url_override: Optional[str] = Field(default=None, alias="DATABASE_URL")
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="postgres")
    db_user: str = Field(default="postgres")
    db_password: str = Field(default="Iamstark@123")

    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    db_pool_recycle_seconds: int = Field(default=280, alias="DB_POOL_RECYCLE_SECONDS")
    db_pool_timeout_seconds: int = Field(default=30, alias="DB_POOL_TIMEOUT_SECONDS")

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return normalize_asyncpg_database_url(self.database_url_override)

        # URL-encode password (because it contains '@')
        pw = quote_plus(self.db_password)
        return f"postgresql+asyncpg://{self.db_user}:{pw}@{self.db_host}:{self.db_port}/{self.db_name}"


class CloudinarySettings(BaseSettings):
    """
    Cloudinary configuration.
    """
    model_config = SettingsConfigDict(env_file=get_env_file(), env_file_encoding="utf-8", extra="ignore")

    cloud_name: Optional[str] = Field(default=None, alias="CLOUDINARY_CLOUD_NAME")
    api_key: Optional[str] = Field(default=None, alias="CLOUDINARY_API_KEY")
    api_secret: Optional[str] = Field(default=None, alias="CLOUDINARY_API_SECRET")

db_settings = DbSettings()
cloudinary_settings = CloudinarySettings()
