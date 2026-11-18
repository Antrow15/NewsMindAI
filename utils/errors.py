"""Application exceptions for the NewsMind console."""

from __future__ import annotations


class AppError(Exception):
    """Base application error with a user-facing message."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ValidationError(AppError):
    """Invalid or missing field values."""


class NotFoundError(AppError):
    """Requested record does not exist."""


class AuthError(AppError):
    """Authentication / session failure."""


class PermissionDeniedError(AppError):
    """Caller lacks required capability."""
