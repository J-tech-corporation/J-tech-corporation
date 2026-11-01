"""Application service for creating and retrieving policy registry entries."""

from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.policy_version import PolicyVersion
from app.repositories.policy_repository import PolicyRepository
from app.schemas.policy import PolicyCreate


class PolicyRegistry:
    """Create draft policies and preserve their initial version snapshot."""

    def __init__(self, session: Session) -> None:
        self.repository = PolicyRepository(session)

    def create_policy(self, payload: PolicyCreate) -> Policy:
        """Create a DRAFT policy and its initial version; caller owns commit."""
        if payload.scope_type.value == "GLOBAL" and payload.scope_id is not None:
            raise ValueError("Global policies must not specify scope_id")
        if payload.scope_type.value != "GLOBAL" and payload.scope_id is None:
            raise ValueError("Non-global policies require scope_id")

        policy = Policy(
            policy_key=payload.policy_key,
            name=payload.name,
            description=payload.description,
            policy_type=payload.policy_type.value,
            scope_type=payload.scope_type.value,
            scope_id=payload.scope_id,
            status="DRAFT",
            current_version=1,
            rules=payload.rules,
            created_by=payload.created_by,
        )
        snapshot = PolicyVersion(
            version=1,
            name=payload.name,
            description=payload.description,
            policy_type=payload.policy_type.value,
            scope_type=payload.scope_type.value,
            scope_id=payload.scope_id,
            rules=payload.rules,
            change_reason="Initial policy creation",
            created_by=payload.created_by,
        )
        return self.repository.create(policy, snapshot)
