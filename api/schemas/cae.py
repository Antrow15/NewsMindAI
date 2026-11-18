"""CAE request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from config.constants import ADAPTATION_PLATFORMS


class AdaptationCreate(BaseModel):
    original_title: str = Field(..., min_length=5, max_length=500)
    original_content: str = Field(..., min_length=20)
    target_platforms: list[str] = Field(..., min_length=1)

    @field_validator("target_platforms")
    @classmethod
    def validate_platforms(cls, value: list[str]) -> list[str]:
        normalized = [str(v).strip().upper() for v in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("target_platforms must not contain duplicates")
        bad = [p for p in normalized if p not in ADAPTATION_PLATFORMS]
        if bad:
            raise ValueError(f"Unsupported platforms: {bad}")
        return normalized


class DraftResponse(BaseModel):
    id: int
    platform: str
    version_number: int
    adapted_title: str
    adapted_content: str
    model_version: str
    status: str
    generation_parameters: dict[str, Any] = Field(default_factory=dict)
    validation_flags: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class AdaptationResponse(BaseModel):
    id: int
    original_title: str
    original_content: str
    created_by: int | None = None
    status: str
    created_at: datetime | None = None
    drafts: list[DraftResponse] = Field(default_factory=list)


class RemarksRequest(BaseModel):
    remarks: str | None = Field(default=None, max_length=2000)


class RequiredRemarksRequest(BaseModel):
    remarks: str = Field(..., min_length=3, max_length=2000)


class FinalVersionRequest(BaseModel):
    final_title: str = Field(..., min_length=5, max_length=500)
    final_content: str = Field(..., min_length=20)
    remarks: str | None = Field(default=None, max_length=2000)
