"""Integration tests for policy-backed permission decisions."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, Policy
from app.schemas.permission import (
    DataClassification,
    PermissionDecision,
    PermissionEvaluationRequest,
)
from app.services.permission_engine import PermissionEngine


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_request(
    classification: DataClassification = DataClassification.INTERNAL,
) -> PermissionEvaluationRequest:
    return PermissionEvaluationRequest(
        subject_id="agent-1",
        subject_type="AGENT",
        resource_id="doc-1",
        resource_type="DOCUMENT",
        action="READ",
        classification=classification,
        purpose="Assigned project work",
        project_id="project-1",
    )


def add_policy(
    session: Session,
    *,
    key: str,
    effect: str,
    status: str = "ACTIVE",
    policy_type: str = "PROJECT",
    rules: dict | None = None,
) -> None:
    session.add(Policy(
        policy_key=key,
        name=key,
        policy_type=policy_type,
        scope_type="PROJECT",
        scope_id="project-1",
        status=status,
        current_version=1,
        rules=rules or {
            "effect": effect,
            "all": [{"field": "action", "operator": "eq", "value": "READ"}],
        },
        created_by="ceo",
    ))
    session.flush()


def test_active_matching_allow_policy_authorizes_request(db_session: Session) -> None:
    add_policy(db_session, key="project.read", effect="ALLOW")
    result = PermissionEngine(db_session).evaluate(make_request())
    assert result.decision is PermissionDecision.ALLOW
    assert result.policies_evaluated == ["project.read"]


def test_deny_overrides_matching_allow_policy(db_session: Session) -> None:
    add_policy(db_session, key="project.allow", effect="ALLOW")
    add_policy(db_session, key="project.deny", effect="DENY")
    result = PermissionEngine(db_session).evaluate(make_request())
    assert result.decision is PermissionDecision.DENY
    assert set(result.policies_evaluated) == {"project.allow", "project.deny"}


def test_non_active_policy_does_not_authorize(db_session: Session) -> None:
    add_policy(db_session, key="project.draft", effect="ALLOW", status="DRAFT")
    result = PermissionEngine(db_session).evaluate(make_request())
    assert result.decision is PermissionDecision.DENY


def test_security_policy_json_does_not_override_code_safeguards(
    db_session: Session,
) -> None:
    add_policy(
        db_session, key="security.fake", effect="ALLOW", policy_type="SECURITY"
    )
    result = PermissionEngine(db_session).evaluate(make_request())
    assert result.decision is PermissionDecision.DENY


def test_restricted_data_still_requires_ceo_approval(db_session: Session) -> None:
    add_policy(db_session, key="project.allow", effect="ALLOW")
    result = PermissionEngine(db_session).evaluate(
        make_request(DataClassification.RESTRICTED)
    )
    assert result.decision is PermissionDecision.REQUIRE_APPROVAL


def test_malformed_active_policy_fails_closed(db_session: Session) -> None:
    add_policy(
        db_session,
        key="project.malformed",
        effect="ALLOW",
        rules={"effect": "ALLOW", "all": [{"field": "not_allowed", "operator": "eq", "value": 1}]},
    )
    result = PermissionEngine(db_session).evaluate(make_request())
    assert result.decision is PermissionDecision.DENY
    assert result.policies_evaluated == ["policy_evaluation_error"]
