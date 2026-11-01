"""Strict schemas for policy approval requests and reviews."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.auth import StrictSchema
from app.schemas.policy import SEMANTIC_VERSION_PATTERN


class ApprovalRequestStatus(StrEnum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ApprovalReviewType(StrEnum):
    SECURITY = "SECURITY"
    POLICY = "POLICY"
    IMPACT = "IMPACT"


class ApprovalDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_CHANGES = "REQUEST_CHANGES"


class PolicyApprovalRequestCreate(StrictSchema):
    policy_id: UUID
    policy_version: str = Field(pattern=SEMANTIC_VERSION_PATTERN)
    snapshot_hash: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    requested_by: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=1000)
    submitted_at: datetime

    @field_validator("requested_by", "reason")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("submitted_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("submitted_at must include a timezone")
        return value.astimezone(timezone.utc)


class PolicyApprovalRequestRead(StrictSchema):
    id: UUID
    policy_id: UUID
    policy_version: str = Field(pattern=SEMANTIC_VERSION_PATTERN)
    snapshot_hash: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    requested_by: str
    status: ApprovalRequestStatus
    reason: str
    submitted_at: datetime


class PolicyApprovalReviewCreate(StrictSchema):
    reviewer_id: str = Field(min_length=1, max_length=128)
    review_type: ApprovalReviewType
    decision: ApprovalDecision
    comments: str | None = Field(default=None, max_length=2000)
    reviewed_at: datetime

    @field_validator("reviewer_id")
    @classmethod
    def reject_blank_reviewer(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reviewer_id must not be blank")
        return value

    @field_validator("comments")
    @classmethod
    def normalize_comments(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("reviewed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at must include a timezone")
        return value.astimezone(timezone.utc)


class PolicyApprovalReviewRead(StrictSchema):
    id: UUID
    approval_request_id: UUID
    reviewer_id: str
    review_type: ApprovalReviewType
    decision: ApprovalDecision
    comments: str | None
    reviewed_at: datetime
