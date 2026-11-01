"""Safe evaluator for the supported JSON business/project policy subset."""

from typing import Any

from app.models.policy import Policy
from app.schemas.permission import PermissionEvaluationRequest


_ALLOWED_FIELDS = {
    "subject_id", "subject_type", "resource_id", "resource_type", "action",
    "classification", "purpose", "project_id", "task_id", "session_id",
}
_ALLOWED_OPERATORS = {"eq", "ne", "in"}


class PolicyEvaluationError(ValueError):
    """Raised when a policy uses an unsupported or malformed rule."""


class PolicyEvaluator:
    """Evaluate declarative rules without executing arbitrary code."""

    def matches_scope(
        self, policy: Policy, request: PermissionEvaluationRequest
    ) -> bool:
        if policy.scope_type == "GLOBAL":
            return policy.scope_id is None
        if policy.scope_type == "PROJECT":
            return request.project_id is not None and policy.scope_id == request.project_id
        if policy.scope_type == "TASK":
            return request.task_id is not None and policy.scope_id == request.task_id
        # Department scope is unavailable in the current request contract.
        return False

    def evaluate(
        self, policy: Policy, request: PermissionEvaluationRequest
    ) -> str | None:
        """Return the effect when all conditions match, otherwise None."""
        if policy.status != "ACTIVE" or policy.policy_type not in {"BUSINESS", "PROJECT"}:
            return None
        if not self.matches_scope(policy, request):
            return None

        rules = policy.rules
        if not isinstance(rules, dict):
            raise PolicyEvaluationError("Policy rules must be an object")

        effect = rules.get("effect")
        if effect not in {"ALLOW", "DENY", "REQUIRE_APPROVAL"}:
            raise PolicyEvaluationError("Policy effect is missing or unsupported")

        conditions = rules.get("all")
        if not isinstance(conditions, list) or not conditions:
            raise PolicyEvaluationError("Policy must contain a non-empty all condition list")

        context: dict[str, Any] = request.model_dump()
        for condition in conditions:
            if not isinstance(condition, dict) or set(condition) != {"field", "operator", "value"}:
                raise PolicyEvaluationError("Each condition must define field, operator, and value")
            field = condition["field"]
            operator = condition["operator"]
            expected = condition["value"]
            if field not in _ALLOWED_FIELDS or operator not in _ALLOWED_OPERATORS:
                raise PolicyEvaluationError(
                    "Policy condition uses an unsupported field or operator"
                )
            if operator == "in" and (
                not isinstance(expected, list) or not expected or len(expected) > 100
            ):
                raise PolicyEvaluationError("The in operator requires a non-empty list")

            actual = context[field]
            if operator == "eq" and actual != expected:
                return None
            if operator == "ne" and actual == expected:
                return None
            if operator == "in" and actual not in expected:
                return None

        return effect
