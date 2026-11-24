"""Shared session + capability gate for modules/services."""

from __future__ import annotations

from typing import Any, Iterable

from modules.authentication.auth_service import AuthenticationError, resolve_session
from services.permission_service import PermissionError, has_capability, require_capability
from utils.errors import AuthError, PermissionDeniedError


def require_capability_session(
    capability: str,
    session_token: str | None = None,
) -> dict[str, Any]:
    try:
        user = resolve_session(session_token)
    except AuthenticationError as exc:
        raise AuthError(str(exc)) from exc
    try:
        require_capability(user["role_code"], capability)
    except PermissionError as exc:
        raise PermissionDeniedError(str(exc)) from exc
    return user


def require_any_capability_session(
    capabilities: Iterable[str],
    session_token: str | None = None,
) -> dict[str, Any]:
    """Session user must hold at least one of the listed capabilities."""
    try:
        user = resolve_session(session_token)
    except AuthenticationError as exc:
        raise AuthError(str(exc)) from exc
    role = user["role_code"]
    caps = [str(c) for c in capabilities if c]
    if any(has_capability(role, c) for c in caps):
        return user
    raise PermissionDeniedError(
        f"Role '{role}' needs one of: {', '.join(caps) or '(none)'}."
    )
