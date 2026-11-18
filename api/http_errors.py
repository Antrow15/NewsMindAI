"""Map app errors to HTTP responses (shared by all routers)."""

from __future__ import annotations

from fastapi import HTTPException, status

from modules.authentication.auth_service import AuthenticationError
from utils.errors import AppError, AuthError, NotFoundError, PermissionDeniedError, ValidationError
from utils.logger import get_logger

log = get_logger("api.http_errors")


def raise_http_error(exc: Exception) -> None:
    """Convert known app errors to HTTPException. Always raises."""
    if isinstance(exc, (AuthError, AuthenticationError)):
        detail = getattr(exc, "message", None) or str(exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
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
    if isinstance(exc, AppError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    # Avoid opaque FastAPI Internal Server Error for unexpected failures
    log.exception("Unhandled API error: %s", exc)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Internal error: {exc}",
    ) from exc
