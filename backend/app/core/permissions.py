"""Small RBAC foundation; persisted roles and policies arrive in later phases."""

from enum import StrEnum


class SystemRole(StrEnum):
    CEO = "CEO"
    EXECUTIVE = "EXECUTIVE"
    EMPLOYEE = "EMPLOYEE"
    AGENT = "AGENT"


def has_role(user_roles: set[str] | list[str], required_role: SystemRole) -> bool:
    """Check role membership without granting implicit CEO approval powers."""
    return required_role.value in {role.upper() for role in user_roles}
