"""Strict schemas for permission evaluation requests and responses."""

from enum import StrEnum

from pydantic import ConfigDict, Field

from app.schemas.auth import StrictSchema


class DataClassification(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    TOP_SECRET = "TOP_SECRET"


class PermissionDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class PermissionEvaluationRequest(StrictSchema):
    """Context supplied by a trusted service for one authorization check."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    subject_id: str = Field(min_length=1, max_length=128)
    subject_type: str = Field(pattern=r"^(USER|AGENT|SERVICE)$")
    resource_id: str = Field(min_length=1, max_length=256)
    resource_type: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=128)
    classification: DataClassification
    purpose: str = Field(min_length=1, max_length=500)
    project_id: str | None = Field(default=None, min_length=1, max_length=128)
    task_id: str | None = Field(default=None, min_length=1, max_length=128)
    session_id: str | None = Field(default=None, min_length=1, max_length=256)
    correlation_id: str | None = Field(default=None, min_length=1, max_length=128)


class PermissionEvaluationResponse(StrictSchema):
    """Normalized decision returned by the permission engine."""

    decision: PermissionDecision
    reason: str = Field(min_length=1, max_length=1000)
    policies_evaluated: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    audit_reference: str = Field(min_length=1, max_length=64)
    evaluation_timestamp: str = Field(min_length=1, max_length=64)
