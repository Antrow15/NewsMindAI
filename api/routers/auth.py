"""Login, logout, change password, profile, admin reset."""

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
    ProfileResponse,
    ProfileUpdateRequest,
)
from config.constants import CAP_MANAGE_USERS
from dao.employee_dao import EmployeeDAO
from dao.user_dao import UserDAO
from database.connection import db_cursor
from modules.authentication.auth_service import (
    AuthenticationError,
    authenticate,
    change_password,
    logout,
)
from services.access import require_capability_session
from services.user import UserService
from utils.errors import AuthError, NotFoundError, PermissionDeniedError, ValidationError
from utils.validators import require_email, require_nonempty, require_optional_str

router = APIRouter(prefix="/auth", tags=["1. Login"])
_APP_ERRORS = (AuthError, PermissionDeniedError, ValidationError, NotFoundError)


def _load_profile(user_id: int) -> dict:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT u.user_id, u.username, u.account_status, u.employee_id,
                   r.role_code, r.role_name,
                   e.employee_code, e.first_name, e.last_name, e.email,
                   e.mobile_number, e.department, e.designation, e.location,
                   e.employment_status, e.joining_date
            FROM users u
            JOIN employee e ON e.employee_id = u.employee_id
            JOIN role r ON r.role_id = u.role_id
            WHERE u.user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        raise NotFoundError("Profile not found.")
    data = dict(row)
    jd = data.get("joining_date")
    if jd is not None and hasattr(jd, "isoformat"):
        data["joining_date"] = jd.isoformat()
    return data


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


@router.get("/me", response_model=ProfileResponse, summary="My profile")
def get_my_profile(user: dict = Depends(get_current_user)):
    try:
        return _load_profile(int(user["user_id"]))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put("/me", response_model=ProfileResponse, summary="Update my profile")
def update_my_profile(
    body: ProfileUpdateRequest,
    user: dict = Depends(get_current_user),
):
    try:
        row = UserDAO().require(int(user["user_id"]))
        employee_id = int(row["employee_id"])
        EmployeeDAO().update(
            employee_id,
            first_name=require_nonempty(body.first_name, "First name"),
            last_name=require_nonempty(body.last_name, "Last name"),
            email=require_email(body.email),
            mobile_number=require_optional_str(body.mobile_number, "Mobile"),
            location=require_optional_str(body.location, "Location", max_len=128),
        )
        return _load_profile(int(user["user_id"]))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


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
