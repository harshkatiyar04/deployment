from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.env import get_env_file


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=get_env_file(), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ZENK BE"

    # Where uploaded KYC docs are stored on disk (local storage for now)
    storage_dir: str = Field(default="app/storage")

    # Public site / invite links (set to production URL on deploy)
    website_url: str = Field(default="http://localhost:5173", validation_alias="WEBSITE_URL")
    frontend_base_url: str = Field(
        default="http://localhost:5173",
        validation_alias="FRONTEND_BASE_URL",
    )

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
    groq_api_key: Optional[str] = Field(default=None)

    # The Guardian Open Platform (use "test" for dev tier; set a real key in production)
    guardian_api_key: Optional[str] = Field(default=None, validation_alias="GUARDIAN_API_KEY")

    # Dev-only: allow auto-join demo circle (never enable in production)
    allow_demo_circle: bool = Field(default=False, validation_alias="ZENK_ALLOW_DEMO_CIRCLE")

    # Admin KYC / queue APIs — required in production (FE: VITE_ZENK_ADMIN_API_KEY)
    admin_api_key: Optional[str] = Field(default=None, validation_alias="ZENK_ADMIN_API_KEY")
    # Local dev only: allow admin routes without a key (never enable in production)
    admin_allow_open_dev: bool = Field(default=False, validation_alias="ZENK_ADMIN_ALLOW_OPEN_DEV")

    # ICICI corporate disbursement gateway (production URL from bank onboarding)
    icici_gateway_base_url: Optional[str] = Field(
        default=None,
        validation_alias="ICICI_GATEWAY_BASE_URL",
    )
    icici_merchant_id: Optional[str] = Field(
        default=None,
        validation_alias="ICICI_MERCHANT_ID",
    )


settings = Settings()


