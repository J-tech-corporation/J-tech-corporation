"""Tests for safe business/project policy evaluation."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, Policy
from app.schemas.permission import PermissionEvaluationRequest
from app.services.policy_evaluator import PolicyEvaluationError, PolicyEvaluator


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_request() -> PermissionEvaluationRequest:
    return PermissionEvaluationRequest(
        subject_id="agent-1", subject_type="AGENT", resource_id="doc-1",
        resource_type="DOCUMENT", action="READ", classification="INTERNAL",
        purpose="Assigned project work", project_id="project-1",
    )


def make_policy(**overrides) -> Policy:
    values = {
        "policy_key": "project.read", "name": "Project read",
        "policy_type": "PROJECT", "scope_type": "PROJECT", "scope_id": "project-1",
        "status": "ACTIVE", "current_version": 1,
        "rules": {"effect": "ALLOW", "all": [
            {"field": "action", "operator": "eq", "value": "READ"}
        ]},
        "created_by": "ceo",
    }
    values.update(overrides)
    return Policy(**values)


def test_matching_project_policy_returns_effect() -> None:
    assert PolicyEvaluator().evaluate(make_policy(), make_request()) == "ALLOW"


def test_non_matching_condition_does_not_match() -> None:
    policy = make_policy(rules={"effect": "ALLOW", "all": [
        {"field": "action", "operator": "eq", "value": "WRITE"}
    ]})
    assert PolicyEvaluator().evaluate(policy, make_request()) is None


def test_policy_scope_must_match_request() -> None:
    assert PolicyEvaluator().evaluate(
        make_policy(scope_id="another-project"), make_request()
    ) is None


@pytest.mark.parametrize("status", ["DRAFT", "PENDING_APPROVAL", "EXPIRED", "SUSPENDED"])
def test_non_active_policy_is_ignored(status: str) -> None:
    assert PolicyEvaluator().evaluate(make_policy(status=status), make_request()) is None


def test_security_policy_json_is_not_executed() -> None:
    policy = make_policy(policy_type="SECURITY", scope_type="GLOBAL", scope_id=None)
    assert PolicyEvaluator().evaluate(policy, make_request()) is None


@pytest.mark.parametrize(
    "rules",
    [None, {}, {"effect": "ALLOW"}, {"effect": "EXECUTE", "all": []},
     {"effect": "ALLOW", "all": [{"field": "__class__", "operator": "eq", "value": "x"}]}],
)
def test_malformed_or_unsupported_rules_fail_closed(rules) -> None:
    with pytest.raises(PolicyEvaluationError):
        PolicyEvaluator().evaluate(make_policy(rules=rules), make_request())


def test_department_scope_fails_closed() -> None:
    policy = make_policy(scope_type="DEPARTMENT", scope_id="engineering")
    assert PolicyEvaluator().evaluate(policy, make_request()) is None
