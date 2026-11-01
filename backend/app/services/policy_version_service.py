"""Create and retrieve immutable semantic-versioned policy snapshots."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.policy_version import PolicyVersion
from app.repositories.policy_repository import PolicyRepository
from app.schemas.policy import increment_semantic_version
from app.services.policy_registry import build_snapshot_hash


class PolicyVersionError(ValueError):
    """Raised when a policy version operation is invalid."""


class PolicyNotFoundError(PolicyVersionError):
    """Raised when the requested policy does not exist."""


class PolicyVersionService:
    """Create policy snapshots; the caller owns transaction commit or rollback."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = PolicyRepository(session)

    def create_version(
        self,
        *,
        policy_id: UUID,
        created_by: str,
        change_reason: str,
        bump: str,
        name: str | None = None,
        description: str | None = None,
        rules: dict | None = None,
    ) -> PolicyVersion:
        """Create the next semantic version while locking its parent policy row."""
        actor = created_by.strip()
        reason = change_reason.strip()
        if not actor:
            raise PolicyVersionError("created_by must not be blank")
        if not reason:
            raise PolicyVersionError("change_reason must not be blank")

        policy = self.repository.get_by_id_for_update(policy_id)
        if policy is None:
            raise PolicyNotFoundError("Policy was not found")

        next_version = increment_semantic_version(policy.current_version, bump)
        if self.repository.get_version(policy_id, next_version) is not None:
            raise PolicyVersionError("Policy version already exists")

        snapshot_name = name.strip() if name is not None else policy.name
        if not snapshot_name:
            raise PolicyVersionError("Policy name must not be blank")
        snapshot_description = (
            description if description is not None else policy.description
        )
        snapshot_rules = rules if rules is not None else policy.rules
        snapshot_hash = build_snapshot_hash(
            version=next_version,
            name=snapshot_name,
            description=snapshot_description,
            policy_type=policy.policy_type,
            scope_type=policy.scope_type,
            scope_id=policy.scope_id,
            rules=snapshot_rules,
            change_reason=reason,
            created_by=actor,
        )
        version = PolicyVersion(
            version=next_version,
            name=snapshot_name,
            description=snapshot_description,
            policy_type=policy.policy_type,
            scope_type=policy.scope_type,
            scope_id=policy.scope_id,
            rules=snapshot_rules,
            change_reason=reason,
            snapshot_hash=snapshot_hash,
            created_by=actor,
        )
        return self.repository.add_version(policy, version)

    def list_versions(self, policy_id: UUID) -> list[PolicyVersion]:
        """Return all snapshots for a policy in creation order."""
        if self.repository.get_by_id(policy_id) is None:
            raise PolicyNotFoundError("Policy was not found")
        return self.repository.list_versions(policy_id)
