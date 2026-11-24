"""Auth request/response bodies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common import MessageResponse
from api.schemas.rules import LoginPasswordStr, StrongPasswordStr, UsernameStr

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "ChangePasswordRequest",
    "AdminResetPasswordRequest",
    "ProfileResponse",
    "ProfileUpdateRequest",
    "MessageResponse",
]


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"username": "journalist", "password": "Journalist@NewsMind2026!"}
            ]
        }
    )

    username: UsernameStr
    password: LoginPasswordStr


class LoginResponse(BaseModel):
    session_token: str = Field(
        description="JWT access token. Paste into Swagger Authorize as Bearer token."
    )
    user_id: int
    username: str
    role_code: str
    capabilities: list[str] = []


class ChangePasswordRequest(BaseModel):
    current_password: LoginPasswordStr
    new_password: StrongPasswordStr = Field(
        ...,
        description="Min 10 chars with upper, lower, digit, and special character.",
    )


class AdminResetPasswordRequest(BaseModel):
    username: UsernameStr
    new_password: StrongPasswordStr = Field(
        ...,
        description="Min 10 chars with upper, lower, digit, and special character.",
    )


class ProfileResponse(BaseModel):
    user_id: int
    username: str
    role_code: str
    role_name: str | None = None
    account_status: str | None = None
    employee_code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    mobile_number: str | None = None
    department: str | None = None
    designation: str | None = None
    location: str | None = None
    employment_status: str | None = None
    joining_date: str | None = None


class ProfileUpdateRequest(BaseModel):
    """Self-service fields employees may edit."""

    first_name: str = Field(..., min_length=1, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., min_length=3, max_length=255)
    mobile_number: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=128)
