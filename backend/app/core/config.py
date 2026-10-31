"""Environment-based application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_prefix="ATECH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "A-TECH Corporation API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    secret_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("ATECH_SECRET_KEY", "SECRET_KEY"),
    )
    database_environment: Literal["local", "cloud"] = "local"
    local_database_url: SecretStr = SecretStr("")
    cloud_database_url: SecretStr = SecretStr("")
    jwt_private_key: SecretStr = SecretStr("")
    jwt_public_key: SecretStr = SecretStr("")
    jwt_key_id: str = "atech-ed25519-1"
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=7, ge=1, le=90)

    @model_validator(mode="after")
    def require_secret_in_production(self) -> "Settings":
        if self.app_env.lower() == "production" and not self.secret_key.get_secret_value():
            raise ValueError("Set ATECH_SECRET_KEY or SECRET_KEY in production")
        return self

    def get_database_url(self) -> str:
        """Return only the URL for the explicitly selected environment."""
        configured_url = (
            self.local_database_url
            if self.database_environment == "local"
            else self.cloud_database_url
        )
        database_url = configured_url.get_secret_value()
        if not database_url:
            raise ValueError(
                f"Database URL is not configured for {self.database_environment!r}"
            )
        return database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for the current process."""
    return Settings()
