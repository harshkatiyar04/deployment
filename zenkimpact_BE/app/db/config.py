from __future__ import annotations

from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.env import get_env_file


from typing import Optional

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

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            # SQLAlchemy async requires postgresql+asyncpg://
            if self.database_url_override.startswith("postgresql://"):
                return self.database_url_override.replace("postgresql://", "postgresql+asyncpg://", 1)
            return self.database_url_override

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
