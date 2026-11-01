"""Persistence operations for policy registry records."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.policy import Policy
from app.models.policy_version import PolicyVersion


class DuplicatePolicyError(ValueError):
    """Raised when a policy key already exists."""


class PolicyRepository:
    """Database access for policy records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, policy: Policy, initial_version: PolicyVersion) -> Policy:
        policy.versions.append(initial_version)
        self.session.add(policy)
        self.session.flush()
        return policy

    def get_by_id(self, policy_id: UUID) -> Policy | None:
        statement = (
            select(Policy)
            .options(selectinload(Policy.versions))
            .where(Policy.id == policy_id)
        )
        return self.session.scalar(statement)

    def get_by_id_for_update(self, policy_id: UUID) -> Policy | None:
        """Lock a policy row while assigning its next version number."""
        statement = select(Policy).where(Policy.id == policy_id).with_for_update()
        return self.session.scalar(statement)

    def get_by_key(self, policy_key: str) -> Policy | None:
        statement = (
            select(Policy)
            .options(selectinload(Policy.versions))
            .where(Policy.policy_key == policy_key)
        )
        return self.session.scalar(statement)

    def get_version(self, policy_id: UUID, version: str) -> PolicyVersion | None:
        statement = select(PolicyVersion).where(
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.version == version,
        )
        return self.session.scalar(statement)

    def list_versions(self, policy_id: UUID) -> list[PolicyVersion]:
        statement = (
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id)
            .order_by(PolicyVersion.created_at, PolicyVersion.version)
        )
        return list(self.session.scalars(statement).all())

    def add_version(self, policy: Policy, version: PolicyVersion) -> PolicyVersion:
        policy.versions.append(version)
        policy.current_version = version.version
        self.session.add(version)
        self.session.flush()
        return version

    def list_policies(
        self,
        *,
        status: str | None = None,
        policy_type: str | None = None,
        limit: int = 100,
    ) -> list[Policy]:
        statement = select(Policy).order_by(Policy.policy_key).limit(limit)
        if status is not None:
            statement = statement.where(Policy.status == status)
        if policy_type is not None:
            statement = statement.where(Policy.policy_type == policy_type)
        return list(self.session.scalars(statement).all())

    def list_active_evaluable_policies(self, *, limit: int = 100) -> list[Policy]:
        """Return active business/project policies; security rules remain code-defined."""
        statement = (
            select(Policy)
            .where(
                Policy.status == "ACTIVE",
                Policy.policy_type.in_(("BUSINESS", "PROJECT")),
            )
            .order_by(Policy.policy_key)
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())
