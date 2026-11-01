"""Tests for policy registry models and service."""

from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Base, Policy, PolicyVersion
from app.schemas.policy import (
    PolicyCreate,
    PolicyScopeType,
    PolicyType,
    increment_semantic_version,
    parse_semantic_version,
)
from app.services.policy_registry import PolicyRegistry, build_snapshot_hash


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_payload(**overrides) -> PolicyCreate:
    values = {
        "policy_key": "project.tasks.read",
        "name": "Read project tasks",
        "description": "Controls reading project tasks",
        "policy_type": PolicyType.PROJECT,
        "scope_type": PolicyScopeType.PROJECT,
        "scope_id": "project-123",
        "rules": {"all": [{"field": "action", "operator": "eq", "value": "read"}]},
        "created_by": "agent-pm",
    }
    values.update(overrides)
    return PolicyCreate.model_validate(values)


def test_create_policy_creates_draft_and_initial_semantic_version(db_session: Session) -> None:
    policy = PolicyRegistry(db_session).create_policy(make_payload())
    db_session.commit()
    assert isinstance(policy.id, UUID)
    assert policy.status == "DRAFT"
    assert policy.current_version == "1.0.0"
    assert len(policy.versions) == 1
    assert policy.versions[0].version == "1.0.0"
    assert len(policy.versions[0].snapshot_hash) == 64
    assert policy.versions[0].change_reason == "Initial policy creation"
    assert policy.versions[0].rules == policy.rules


def test_snapshot_hash_is_deterministic() -> None:
    first = build_snapshot_hash(
        version="1.0.0",
        name="Policy",
        description=None,
        policy_type="BUSINESS",
        scope_type="GLOBAL",
        scope_id=None,
        rules={"z": 1, "a": 2},
        change_reason="Initial",
        created_by="ceo",
    )
    second = build_snapshot_hash(
        version="1.0.0",
        name="Policy",
        description=None,
        policy_type="BUSINESS",
        scope_type="GLOBAL",
        scope_id=None,
        rules={"a": 2, "z": 1},
        change_reason="Initial",
        created_by="ceo",
    )
    assert first == second


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("0.0.0", (0, 0, 0)),
        ("1.2.3", (1, 2, 3)),
        ("12.0.10", (12, 0, 10)),
    ],
)
def test_parse_semantic_version(version: str, expected: tuple[int, int, int]) -> None:
    assert parse_semantic_version(version) == expected


@pytest.mark.parametrize("version", ["1", "1.2", "01.2.3", "1.02.3", "v1.2.3", "1.2.3-beta"])
def test_parse_semantic_version_rejects_invalid_values(version: str) -> None:
    with pytest.raises(ValueError):
        parse_semantic_version(version)


@pytest.mark.parametrize(
    ("version", "bump", "expected"),
    [
        ("1.2.3", "major", "2.0.0"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "patch", "1.2.4"),
    ],
)
def test_increment_semantic_version(version: str, bump: str, expected: str) -> None:
    assert increment_semantic_version(version, bump) == expected


def test_increment_semantic_version_rejects_unknown_bump() -> None:
    with pytest.raises(ValueError, match="Bump"):
        increment_semantic_version("1.2.3", "build")


def test_global_policy_does_not_accept_scope_id(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Global policies"):
        PolicyRegistry(db_session).create_policy(
            make_payload(scope_type=PolicyScopeType.GLOBAL, scope_id="not-allowed")
        )


def test_non_global_policy_requires_scope_id(db_session: Session) -> None:
    with pytest.raises(ValueError, match="require scope_id"):
        PolicyRegistry(db_session).create_policy(make_payload(scope_id=None))


def test_duplicate_policy_key_is_rejected(db_session: Session) -> None:
    registry = PolicyRegistry(db_session)
    registry.create_policy(make_payload())
    db_session.commit()
    with pytest.raises(IntegrityError):
        registry.create_policy(make_payload(name="Duplicate"))


def test_policy_version_numbers_are_unique_per_policy(db_session: Session) -> None:
    policy = Policy(
        policy_key="security.session.mfa",
        name="Require MFA",
        policy_type="SECURITY",
        scope_type="GLOBAL",
        status="DRAFT",
        current_version="1.0.0",
        created_by="ceo",
    )
    db_session.add(policy)
    db_session.flush()
    db_session.add_all(
        [
            PolicyVersion(
                policy_id=policy.id,
                version="1.0.0",
                name="Require MFA",
                policy_type="SECURITY",
                scope_type="GLOBAL",
                change_reason="Initial",
                snapshot_hash="a" * 64,
                created_by="ceo",
            ),
            PolicyVersion(
                policy_id=policy.id,
                version="1.0.0",
                name="Duplicate",
                policy_type="SECURITY",
                scope_type="GLOBAL",
                change_reason="Duplicate",
                snapshot_hash="b" * 64,
                created_by="ceo",
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_policy_schema_rejects_invalid_key_and_extra_fields() -> None:
    with pytest.raises(ValueError):
        make_payload(policy_key="invalid key")
    with pytest.raises(ValueError):
        make_payload(unapproved_field=True)


def test_policy_repository_filters_by_status_and_type(db_session: Session) -> None:
    from app.repositories.policy_repository import PolicyRepository

    registry = PolicyRegistry(db_session)
    registry.create_policy(make_payload())
    registry.create_policy(
        make_payload(
            policy_key="business.leave.approval",
            policy_type=PolicyType.BUSINESS,
            scope_type=PolicyScopeType.GLOBAL,
            scope_id=None,
            name="Leave approval",
        )
    )
    db_session.commit()
    repository = PolicyRepository(db_session)
    assert len(repository.list_policies(status="DRAFT")) == 2
    assert len(repository.list_policies(policy_type="BUSINESS")) == 1
