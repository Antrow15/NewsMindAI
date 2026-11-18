"""RBAC helpers — role_code → capabilities (your desk model)."""

from __future__ import annotations

from typing import Iterable

from config.constants import ROLE_ADMIN, ROLE_CAPABILITIES


class PermissionError(Exception):
    pass


def capabilities_for_role(role_code: str) -> tuple[str, ...]:
    return ROLE_CAPABILITIES.get(role_code, ())


def has_capability(role_code: str, capability: str) -> bool:
    if role_code == ROLE_ADMIN:
        return True
    return capability in capabilities_for_role(role_code)


def require_roles(role_code: str, allowed: Iterable[str]) -> None:
    allowed_set = set(allowed)
    if role_code == ROLE_ADMIN or role_code in allowed_set:
        return
    raise PermissionError(f"Role '{role_code}' is not allowed for this action.")


def require_capability(role_code: str, capability: str) -> None:
    if has_capability(role_code, capability):
        return
    raise PermissionError(f"Role '{role_code}' lacks capability '{capability}'.")
