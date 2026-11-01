"""Application service for creating and retrieving policy registry entries."""

import hashlib
import json

from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.policy_version import PolicyVersion
from app.repositories.policy_repository import PolicyRepository
from app.schemas.policy import PolicyCreate


def build_snapshot_hash(
    *,
    version: str,
    name: str,
    description: str | None,
    policy_type: str,
    scope_type: str,
    scope_id: str | None,
    rules: dict | None,
    change_reason: str,
    created_by: str,
) -> str:
    """Create a deterministic SHA-256 digest for a policy version snapshot."""
    snapshot = {
        "version": version,
        "name": name,
        "description": description,
        "policy_type": policy_type,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "rules": rules,
        "change_reason": change_reason,
        "created_by": created_by,
    }
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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

        initial_version = "1.0.0"
        change_reason = "Initial policy creation"
        snapshot_hash = build_snapshot_hash(
            version=initial_version,
            name=payload.name,
            description=payload.description,
            policy_type=payload.policy_type.value,
            scope_type=payload.scope_type.value,
            scope_id=payload.scope_id,
            rules=payload.rules,
            change_reason=change_reason,
            created_by=payload.created_by,
        )
        policy = Policy(
            policy_key=payload.policy_key,
            name=payload.name,
            description=payload.description,
            policy_type=payload.policy_type.value,
            scope_type=payload.scope_type.value,
            scope_id=payload.scope_id,
            status="DRAFT",
            current_version=initial_version,
            rules=payload.rules,
            created_by=payload.created_by,
        )
        snapshot = PolicyVersion(
            version=initial_version,
            name=payload.name,
            description=payload.description,
            policy_type=payload.policy_type.value,
            scope_type=payload.scope_type.value,
            scope_id=payload.scope_id,
            rules=payload.rules,
            change_reason=change_reason,
            snapshot_hash=snapshot_hash,
            created_by=payload.created_by,
        )
        return self.repository.create(policy, snapshot)
