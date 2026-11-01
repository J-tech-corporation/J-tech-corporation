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
        statement = select(Policy).options(selectinload(Policy.versions)).where(Policy.id == policy_id)
        return self.session.scalar(statement)

    def get_by_key(self, policy_key: str) -> Policy | None:
        statement = select(Policy).options(selectinload(Policy.versions)).where(Policy.policy_key == policy_key)
        return self.session.scalar(statement)

    def list_policies(self, *, status: str | None = None, policy_type: str | None = None, limit: int = 100) -> list[Policy]:
        statement = select(Policy).order_by(Policy.policy_key).limit(limit)
        if status is not None:
            statement = statement.where(Policy.status == status)
        if policy_type is not None:
            statement = statement.where(Policy.policy_type == policy_type)
        return list(self.session.scalars(statement).all())
