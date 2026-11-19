"""FastAPI dependencies — Bearer session token → current user."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from modules.authentication.auth_service import AuthenticationError, resolve_session

bearer_scheme = HTTPBearer(auto_error=False)


def get_session_token(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login first, then Authorize with your JWT session_token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return creds.credentials.strip()


def get_current_user(token: str = Depends(get_session_token)) -> dict[str, Any]:
    try:
        return resolve_session(token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
