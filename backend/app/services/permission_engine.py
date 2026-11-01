"""Fail-closed core for permission evaluation.

Policy grants are intentionally not implemented in this batch. Until the policy
evaluation layer is delivered, this core must never manufacture an ALLOW result.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.permission import (
    DataClassification,
    PermissionDecision,
    PermissionEvaluationRequest,
    PermissionEvaluationResponse,
)


class PermissionEngine:
    """Create safe, normalized authorization decisions."""

    _APPROVAL_REQUIRED_CLASSIFICATIONS = {
        DataClassification.RESTRICTED,
        DataClassification.TOP_SECRET,
    }

    def evaluate(
        self, request: PermissionEvaluationRequest
    ) -> PermissionEvaluationResponse:
        """Evaluate the safe baseline without granting unverified permissions.

        Restricted and Top Secret requests are routed to the approval workflow.
        All other requests are denied until a verified policy evaluator is added
        in the next sub-batch.
        """
        audit_reference = str(uuid4())
        timestamp = datetime.now(UTC).isoformat()

        if request.classification in self._APPROVAL_REQUIRED_CLASSIFICATIONS:
            return PermissionEvaluationResponse(
                decision=PermissionDecision.REQUIRE_APPROVAL,
                reason=(
                    "CEO approval is required for Restricted and Top Secret data."
                ),
                policies_evaluated=["data_classification:approval_required"],
                conditions=["CEO approval must be verified before access."],
                audit_reference=audit_reference,
                evaluation_timestamp=timestamp,
            )

        return PermissionEvaluationResponse(
            decision=PermissionDecision.DENY,
            reason=(
                "No verified policy evaluator is configured; access is denied "
                "by the fail-closed baseline."
            ),
            policies_evaluated=["default_deny"],
            conditions=["A verified permission policy must authorize this action."],
            audit_reference=audit_reference,
            evaluation_timestamp=timestamp,
        )
