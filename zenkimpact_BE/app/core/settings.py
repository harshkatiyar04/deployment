from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.env import get_env_file


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=get_env_file(), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ZENK BE"

    # Where uploaded KYC docs are stored on disk (local storage for now)
    storage_dir: str = Field(default="app/storage")

    # Website (used in email content)
    website_url: str = Field(default="https://zenkedu.com")

    # SMTP (for email notifications)
    smtp_enabled: bool = Field(default=False)
    smtp_host: Optional[str] = Field(default=None)
    smtp_port: int = Field(default=587)
    smtp_username: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    smtp_use_starttls: bool = Field(default=True)

    # Email identities / routing
    email_from: str = Field(default="leninstark@gmail.com")
    admin_notification_to: str = Field(default="leninstark@gmail.com")
    # Content Moderation API
    gemini_api_key: Optional[str] = Field(default=None)


settings = Settings()


