"""Login, logout, change password, admin reset."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user, get_session_token
from api.http_errors import raise_http_error
from api.schemas.auth import (
    AdminResetPasswordRequest,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
)
from config.constants import CAP_MANAGE_USERS
from modules.authentication.auth_service import (
    AuthenticationError,
    authenticate,
    change_password,
    logout,
)
from services.access import require_capability_session
from services.user import UserService
from utils.errors import AuthError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/auth", tags=["1. Login"])
_APP_ERRORS = (AuthError, PermissionDeniedError, ValidationError)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login",
    description="Returns a JWT in `session_token`. Click **Authorize**, choose Bearer, paste the token.",
)
def login(body: LoginRequest) -> LoginResponse:
    try:
        payload = authenticate(body.username, body.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return LoginResponse(
        session_token=str(payload["session_token"]),
        user_id=int(payload["user_id"]),
        username=str(payload["username"]),
        role_code=str(payload["role_code"]),
        capabilities=list(payload.get("capabilities") or []),
    )


@router.post("/logout", response_model=MessageResponse, summary="Logout")
def do_logout(token: str = Depends(get_session_token)) -> MessageResponse:
    logout(token)
    return MessageResponse(message="Logged out.")


@router.post("/change-password", response_model=MessageResponse, summary="Change password")
def do_change_password(
    body: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
):
    try:
        change_password(int(user["user_id"]), body.current_password, body.new_password)
        return MessageResponse(message="Password changed.")
    except ValidationError as exc:
        raise_http_error(exc)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post(
    "/admin/reset-password",
    response_model=MessageResponse,
    summary="Admin reset password",
)
def do_admin_reset_password(
    body: AdminResetPasswordRequest,
    token: str = Depends(get_session_token),
):
    try:
        require_capability_session(CAP_MANAGE_USERS, token)
        UserService().reset_password(body.username, body.new_password, session_token=token)
        return MessageResponse(message=f"Password reset for {body.username}.")
    except _APP_ERRORS as exc:
        raise_http_error(exc)
