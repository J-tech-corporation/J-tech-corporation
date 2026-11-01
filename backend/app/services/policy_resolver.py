"""Deterministic combination of policy effects."""

from app.schemas.permission import PermissionDecision


class PolicyResolver:
    """Resolve effects using strictest-decision-wins."""

    _PRIORITY = {
        PermissionDecision.DENY: 3,
        PermissionDecision.REQUIRE_APPROVAL: 2,
        PermissionDecision.ALLOW: 1,
    }

    def resolve(self, decisions: list[PermissionDecision]) -> PermissionDecision:
        if not decisions:
            return PermissionDecision.DENY
        return max(decisions, key=self._PRIORITY.__getitem__)
