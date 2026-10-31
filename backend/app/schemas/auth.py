"""Authentication request and response schemas."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.core.security import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BootstrapRequest(StrictSchema):
    bootstrap_secret: SecretStr = Field(min_length=1, max_length=4096)
    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(min_length=1, max_length=160)
    password: SecretStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("A valid email address is required")
        return value

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name must not be blank")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
            raise ValueError("Password must be between 12 and 1024 characters")
        return value


class LoginRequest(StrictSchema):
    email: str = Field(min_length=3, max_length=320)
    password: SecretStr = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("A valid email address is required")
        return value


class MFAVerificationRequest(StrictSchema):
    challenge_id: str = Field(min_length=1, max_length=256)
    code: str = Field(min_length=6, max_length=32)


class PasswordResetRequest(StrictSchema):
    token: SecretStr = Field(min_length=32, max_length=4096)
    new_password: SecretStr

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
            raise ValueError("Password must be between 12 and 1024 characters")
        return value


class PasswordChangeRequest(StrictSchema):
    current_password: SecretStr = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: SecretStr

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
            raise ValueError("Password must be between 12 and 1024 characters")
        return value


class TokenResponse(StrictSchema):
    access_token: str = Field(min_length=1)
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(gt=0)
