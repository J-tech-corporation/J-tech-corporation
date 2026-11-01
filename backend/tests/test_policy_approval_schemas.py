"""Tests for policy approval Pydantic schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.policy_approval import (
    ApprovalDecision,
    ApprovalRequestStatus,
    ApprovalReviewType,
    PolicyApprovalRequestCreate,
    PolicyApprovalRequestRead,
    PolicyApprovalReviewCreate,
    PolicyApprovalReviewRead,
)


def test_approval_request_schema_normalizes_text_and_timezone() -> None:
    submitted = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
    payload = PolicyApprovalRequestCreate(
        policy_id=uuid4(),
        policy_version="1.2.3",
        snapshot_hash="b" * 64,
        requested_by="  agent-1  ",
        reason="  Please review  ",
        submitted_at=submitted,
    )

    assert payload.requested_by == "agent-1"
    assert payload.reason == "Please review"
    assert payload.submitted_at.tzinfo is not None


def test_approval_request_rejects_invalid_hash_and_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        PolicyApprovalRequestCreate(
            policy_id=uuid4(),
            policy_version="1.2.3",
            snapshot_hash="invalid",
            requested_by="agent-1",
            reason="Review",
            submitted_at=datetime(2026, 11, 1, 10, 0),
        )


def test_approval_review_schema_accepts_decision_enums() -> None:
    payload = PolicyApprovalReviewCreate(
        reviewer_id="ceo",
        review_type=ApprovalReviewType.POLICY,
        decision=ApprovalDecision.APPROVE,
        comments="  Looks good  ",
        reviewed_at=datetime(2026, 11, 1, 10, 0, tzinfo=UTC),
    )

    assert payload.comments == "Looks good"
    assert payload.decision == ApprovalDecision.APPROVE
    assert ApprovalRequestStatus.PENDING_APPROVAL == "PENDING_APPROVAL"


def test_approval_review_read_schema_requires_ids_and_fields() -> None:
    payload = PolicyApprovalReviewRead(
        id=uuid4(),
        approval_request_id=uuid4(),
        reviewer_id="ceo",
        review_type=ApprovalReviewType.SECURITY,
        decision=ApprovalDecision.REQUEST_CHANGES,
        comments=None,
        reviewed_at=datetime(2026, 11, 1, 10, 0, tzinfo=UTC),
    )

    assert payload.reviewer_id == "ceo"
    assert payload.decision == "REQUEST_CHANGES"


def test_request_read_schema_uses_controlled_status() -> None:
    payload = PolicyApprovalRequestRead(
        id=uuid4(),
        policy_id=uuid4(),
        policy_version="2.0.0",
        snapshot_hash="c" * 64,
        requested_by="agent-1",
        status=ApprovalRequestStatus.APPROVED,
        reason="Approved",
        submitted_at=datetime(2026, 11, 1, 10, 0, tzinfo=UTC),
    )

    assert payload.status == ApprovalRequestStatus.APPROVED
