"""Strict schemas for policy registry operations."""

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.auth import StrictSchema


class PolicyType(StrEnum):
    SECURITY = "SECURITY"
    BUSINESS = "BUSINESS"
    PROJECT = "PROJECT"


class PolicyScopeType(StrEnum):
    GLOBAL = "GLOBAL"
    DEPARTMENT = "DEPARTMENT"
    PROJECT = "PROJECT"
    TASK = "TASK"


class PolicyStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"


class PolicyCreate(StrictSchema):
    policy_key: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9._:-]+$")
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    policy_type: PolicyType
    scope_type: PolicyScopeType
    scope_id: str | None = Field(default=None, min_length=1, max_length=128)
    rules: dict[str, Any] | None = None
    created_by: str = Field(min_length=1, max_length=128)

    @field_validator("name", "created_by")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value


class PolicyRead(StrictSchema):
    id: UUID
    policy_key: str
    name: str
    description: str | None
    policy_type: PolicyType
    scope_type: PolicyScopeType
    scope_id: str | None
    status: PolicyStatus
    current_version: int
    rules: dict[str, Any] | None
    created_by: str


class PolicyVersionRead(StrictSchema):
    id: UUID
    policy_id: UUID
    version: int
    name: str
    description: str | None
    policy_type: PolicyType
    scope_type: PolicyScopeType
    scope_id: str | None
    rules: dict[str, Any] | None
    change_reason: str
    created_by: str
