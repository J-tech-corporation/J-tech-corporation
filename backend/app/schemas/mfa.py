"""Strict request and response schemas for MFA and trusted devices."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MFASetupResponse(StrictSchema):
    method_id: UUID
    secret: str
    provisioning_uri: str


class MFACodeRequest(StrictSchema):
    code: str = Field(pattern=r"^\d{6}$")


class RecoveryCodesResponse(StrictSchema):
    recovery_codes: list[str] = Field(min_length=1, max_length=20)


class TrustedDeviceCreateRequest(StrictSchema):
    device_name: str | None = Field(default=None, max_length=160)
    duration_days: Literal[7, 30, 90] = 30


class TrustedDeviceResponse(StrictSchema):
    id: UUID
    device_name: str | None
    created_at: str
    expires_at: str
    last_used_at: str | None
