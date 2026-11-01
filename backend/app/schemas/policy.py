"""Strict schemas for policy registry operations."""

import re
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.auth import StrictSchema


SEMANTIC_VERSION_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"


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
    current_version: str = Field(pattern=SEMANTIC_VERSION_PATTERN)
    rules: dict[str, Any] | None
    created_by: str


class PolicyVersionRead(StrictSchema):
    id: UUID
    policy_id: UUID
    version: str = Field(pattern=SEMANTIC_VERSION_PATTERN)
    name: str
    description: str | None
    policy_type: PolicyType
    scope_type: PolicyScopeType
    scope_id: str | None
    rules: dict[str, Any] | None
    change_reason: str
    snapshot_hash: str = Field(min_length=64, max_length=64)
    created_by: str


def parse_semantic_version(version: str) -> tuple[int, int, int]:
    """Parse a strict MAJOR.MINOR.PATCH version string."""
    if not re.fullmatch(SEMANTIC_VERSION_PATTERN, version):
        raise ValueError("Version must use MAJOR.MINOR.PATCH format")
    return tuple(int(part) for part in version.split("."))


def increment_semantic_version(version: str, bump: str) -> str:
    """Increment one semantic-version component and reset lower components."""
    major, minor, patch = parse_semantic_version(version)
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError("Bump must be major, minor, or patch")
