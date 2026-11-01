"""Tests for semantic policy version creation and immutable snapshots."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base
from app.schemas.policy import PolicyCreate, PolicyScopeType, PolicyType
from app.services.policy_registry import PolicyRegistry
from app.services.policy_version_service import (
    PolicyNotFoundError,
    PolicyVersionError,
    PolicyVersionService,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def create_policy(session: Session):
    payload = PolicyCreate(
        policy_key="project.tasks.read",
        name="Read project tasks",
        description="Initial description",
        policy_type=PolicyType.PROJECT,
        scope_type=PolicyScopeType.PROJECT,
        scope_id="project-123",
        rules={"action": "read"},
        created_by="agent-pm",
    )
    return PolicyRegistry(session).create_policy(payload)


def test_create_minor_version_copies_and_hashes_snapshot(db_session: Session) -> None:
    policy = create_policy(db_session)
    version = PolicyVersionService(db_session).create_version(
        policy_id=policy.id,
        created_by="agent-pm",
        change_reason="Add task filtering",
        bump="minor",
        rules={"action": "read", "filter": "assigned"},
    )
    db_session.commit()

    assert version.version == "1.1.0"
    assert version.rules == {"action": "read", "filter": "assigned"}
    assert version.name == "Read project tasks"
    assert len(version.snapshot_hash) == 64
    assert policy.current_version == "1.1.0"
    assert policy.versions[0].version == "1.0.0"


@pytest.mark.parametrize(
    ("bump", "expected"),
    [("major", "2.0.0"), ("minor", "1.1.0"), ("patch", "1.0.1")],
)
def test_create_version_supports_each_semver_component(
    db_session: Session, bump: str, expected: str
) -> None:
    policy = create_policy(db_session)
    version = PolicyVersionService(db_session).create_version(
        policy_id=policy.id,
        created_by="ceo",
        change_reason="Version increment test",
        bump=bump,
    )
    assert version.version == expected


def test_create_version_rejects_blank_actor_or_reason(db_session: Session) -> None:
    policy = create_policy(db_session)
    service = PolicyVersionService(db_session)
    with pytest.raises(PolicyVersionError, match="created_by"):
        service.create_version(
            policy_id=policy.id,
            created_by=" ",
            change_reason="Reason",
            bump="patch",
        )
    with pytest.raises(PolicyVersionError, match="change_reason"):
        service.create_version(
            policy_id=policy.id,
            created_by="ceo",
            change_reason=" ",
            bump="patch",
        )


def test_create_version_rejects_unknown_bump(db_session: Session) -> None:
    policy = create_policy(db_session)
    with pytest.raises(ValueError, match="Bump"):
        PolicyVersionService(db_session).create_version(
            policy_id=policy.id,
            created_by="ceo",
            change_reason="Invalid bump",
            bump="build",
        )


def test_create_version_rejects_missing_policy(db_session: Session) -> None:
    with pytest.raises(PolicyNotFoundError):
        PolicyVersionService(db_session).create_version(
            policy_id=uuid4(),
            created_by="ceo",
            change_reason="Missing policy",
            bump="patch",
        )


def test_list_versions_returns_all_snapshots(db_session: Session) -> None:
    policy = create_policy(db_session)
    service = PolicyVersionService(db_session)
    service.create_version(
        policy_id=policy.id,
        created_by="ceo",
        change_reason="First change",
        bump="minor",
    )
    service.create_version(
        policy_id=policy.id,
        created_by="ceo",
        change_reason="Second change",
        bump="patch",
    )
    versions = service.list_versions(policy.id)
    assert [version.version for version in versions] == ["1.0.0", "1.1.0", "1.1.1"]
