"""Shared request/response pieces used by multiple endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentItem(BaseModel):
    """One article or evidence snippet for search / compare."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "title": "Budget vote in parliament",
                    "text": "Parliament held a budget vote today.",
                }
            ]
        }
    )

    id: int | str | None = None
    title: str = ""
    text: str = ""


class MessageResponse(BaseModel):
    message: str


class RankedListResponse(BaseModel):
    actor: str
    results: list[dict[str, Any]] = []
