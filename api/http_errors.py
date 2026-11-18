"""Map app errors to HTTP responses (shared by all routers)."""

from __future__ import annotations

from fastapi import HTTPException, status

from utils.errors import AuthError, NotFoundError, PermissionDeniedError, ValidationError


def raise_http_error(exc: Exception) -> None:
    """Convert known app errors to HTTPException. Always raises."""
    if isinstance(exc, AuthError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        ) from exc
    if isinstance(exc, PermissionDeniedError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
        ) from exc
    if isinstance(exc, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if isinstance(exc, ValidationError):
        detail = getattr(exc, "message", None) or str(exc)
        if "No trained model" in detail:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc
    raise exc
