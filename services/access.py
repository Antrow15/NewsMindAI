"""Shared session + capability gate for modules/services."""

from __future__ import annotations

from typing import Any

from modules.authentication.auth_service import AuthenticationError, resolve_session
from services.permission_service import PermissionError, require_capability
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
