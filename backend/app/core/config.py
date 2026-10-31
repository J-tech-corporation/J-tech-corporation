"""Environment-based application settings."""

from functools import lru_cache

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

    @model_validator(mode="after")
    def require_secret_in_production(self) -> "Settings":
        if self.app_env.lower() == "production" and not self.secret_key.get_secret_value():
            raise ValueError("Set ATECH_SECRET_KEY or SECRET_KEY in production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for the current process."""
    return Settings()
