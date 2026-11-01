"""Tests for the fail-closed permission evaluation core."""

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.permission import (
    DataClassification,
    PermissionDecision,
    PermissionEvaluationRequest,
)
from app.services.permission_engine import PermissionEngine


def make_request(
    classification: DataClassification = DataClassification.INTERNAL,
) -> PermissionEvaluationRequest:
    return PermissionEvaluationRequest(
        subject_id="agent-123",
        subject_type="AGENT",
        resource_id="document-456",
        resource_type="DOCUMENT",
        action="READ",
        classification=classification,
        purpose="Complete assigned project research",
        project_id="project-1",
        task_id="task-1",
        session_id="session-1",
        correlation_id="correlation-1",
    )


def test_unverified_internal_access_is_denied() -> None:
    result = PermissionEngine().evaluate(make_request())

    assert result.decision is PermissionDecision.DENY
    assert "default_deny" in result.policies_evaluated
    assert result.audit_reference
    UUID(result.audit_reference)
    datetime.fromisoformat(result.evaluation_timestamp)


@pytest.mark.parametrize(
    "classification",
    [DataClassification.RESTRICTED, DataClassification.TOP_SECRET],
)
def test_restricted_data_requires_approval(
    classification: DataClassification,
) -> None:
    result = PermissionEngine().evaluate(make_request(classification))

    assert result.decision is PermissionDecision.REQUIRE_APPROVAL
    assert "data_classification:approval_required" in result.policies_evaluated
    assert "CEO approval" in result.reason


def test_public_request_does_not_receive_implicit_allow() -> None:
    result = PermissionEngine().evaluate(make_request(DataClassification.PUBLIC))

    assert result.decision is not PermissionDecision.ALLOW
    assert result.decision is PermissionDecision.DENY


def test_request_rejects_unknown_fields() -> None:
    payload = make_request().model_dump()
    payload["unexpected"] = "value"

    with pytest.raises(ValidationError):
        PermissionEvaluationRequest.model_validate(payload)


def test_request_rejects_blank_required_context() -> None:
    payload = make_request().model_dump()
    payload["purpose"] = "   "

    with pytest.raises(ValidationError):
        PermissionEvaluationRequest.model_validate(payload)
