"""Fail-closed permission evaluation with active policy integration."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.policy_repository import PolicyRepository
from app.schemas.permission import (
    DataClassification,
    PermissionDecision,
    PermissionEvaluationRequest,
    PermissionEvaluationResponse,
)
from app.services.policy_evaluator import PolicyEvaluationError, PolicyEvaluator
from app.services.policy_resolver import PolicyResolver


class PermissionEngine:
    """Evaluate trusted code-level safeguards and active business/project policies."""

    _APPROVAL_REQUIRED_CLASSIFICATIONS = {
        DataClassification.RESTRICTED,
        DataClassification.TOP_SECRET,
    }

    def __init__(self, session: Session | None = None) -> None:
        self.repository = PolicyRepository(session) if session is not None else None
        self.evaluator = PolicyEvaluator()
        self.resolver = PolicyResolver()

    def evaluate(
        self, request: PermissionEvaluationRequest
    ) -> PermissionEvaluationResponse:
        """Evaluate policies; any evaluation failure is handled as DENY."""
        audit_reference = str(uuid4())
        timestamp = datetime.now(UTC).isoformat()

        if request.classification in self._APPROVAL_REQUIRED_CLASSIFICATIONS:
            return PermissionEvaluationResponse(
                decision=PermissionDecision.REQUIRE_APPROVAL,
                reason="CEO approval is required for Restricted and Top Secret data.",
                policies_evaluated=["data_classification:approval_required"],
                conditions=["CEO approval must be verified before access."],
                audit_reference=audit_reference,
                evaluation_timestamp=timestamp,
            )

        if self.repository is None:
            return self._deny(
                audit_reference, timestamp, ["default_deny"],
                "No policy repository is configured; access is denied.",
            )

        try:
            policies = self.repository.list_active_evaluable_policies()
            decisions: list[PermissionDecision] = []
            evaluated: list[str] = []
            for policy in policies:
                effect = self.evaluator.evaluate(policy, request)
                if effect is None:
                    continue
                evaluated.append(policy.policy_key)
                decisions.append(PermissionDecision(effect))

            if not decisions:
                return self._deny(
                    audit_reference, timestamp, evaluated or ["default_deny"],
                    "No active policy matched this request; access is denied.",
                )

            decision = self.resolver.resolve(decisions)
            return PermissionEvaluationResponse(
                decision=decision,
                reason=f"Access decision resolved from {len(evaluated)} active policy match(es).",
                policies_evaluated=evaluated,
                conditions=[
                    "Only active business/project policies with supported rules are evaluated."
                ],
                audit_reference=audit_reference,
                evaluation_timestamp=timestamp,
            )
        except (PolicyEvaluationError, ValueError, TypeError, KeyError, SQLAlchemyError):
            return self._deny(
                audit_reference, timestamp, ["policy_evaluation_error"],
                "A policy could not be evaluated safely; access is denied.",
            )

    @staticmethod
    def _deny(
        audit_reference: str,
        timestamp: str,
        policies: list[str],
        reason: str,
    ) -> PermissionEvaluationResponse:
        return PermissionEvaluationResponse(
            decision=PermissionDecision.DENY,
            reason=reason,
            policies_evaluated=policies,
            conditions=["Fail-closed: a verified matching policy is required."],
            audit_reference=audit_reference,
            evaluation_timestamp=timestamp,
        )
