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
    session_token: str = Field(description="Paste into Swagger Authorize as Bearer token")
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
