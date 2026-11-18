"""Admin / pipeline request and response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.rules import StrongPasswordStr, UsernameStr


class IngestRequest(BaseModel):
    only_new: bool = False


class IngestFileRequest(BaseModel):
    source_file: str = Field(..., min_length=1, description="CSV path relative to data/raw")


class PipelineRequest(BaseModel):
    only_new: bool = False


class CleanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PersistRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AddUserRequest(BaseModel):
    username: UsernameStr
    password: StrongPasswordStr
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)
    role_code: str = Field(default="journalist", min_length=1)
    employee_code: str | None = None


class ResetPasswordRequest(BaseModel):
    username: UsernameStr
    new_password: StrongPasswordStr


class AddCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""


class AdminActionResponse(BaseModel):
    message: str = ""
    result: dict[str, Any] = Field(default_factory=dict)