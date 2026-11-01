"""Tests for strictest-decision-wins policy resolution."""

import pytest

from app.schemas.permission import PermissionDecision
from app.services.policy_resolver import PolicyResolver


@pytest.mark.parametrize(
    ("decisions", "expected"),
    [
        ([PermissionDecision.ALLOW], PermissionDecision.ALLOW),
        ([PermissionDecision.ALLOW, PermissionDecision.REQUIRE_APPROVAL],
         PermissionDecision.REQUIRE_APPROVAL),
        ([PermissionDecision.ALLOW, PermissionDecision.DENY], PermissionDecision.DENY),
        ([PermissionDecision.REQUIRE_APPROVAL, PermissionDecision.DENY],
         PermissionDecision.DENY),
        ([], PermissionDecision.DENY),
    ],
)
def test_resolver_uses_strictest_decision(decisions, expected) -> None:
    assert PolicyResolver().resolve(decisions) is expected
