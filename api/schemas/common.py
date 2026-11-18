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


class SearchRequest(BaseModel):
    """Query plus optional documents to rank against."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "budget vote",
                    "documents": [
                        {
                            "id": 1,
                            "title": "Budget vote in parliament",
                            "text": "Parliament held a budget vote today.",
                        }
                    ],
                    "limit": 5,
                }
            ]
        }
    )

    query: str = Field(..., min_length=1, description="Search text")
    documents: list[DocumentItem] = Field(
        default_factory=list,
        description="Current-draft docs only (do not reuse other stories' evidence)",
    )
    content_id: int | None = Field(
        default=None,
        gt=0,
        description="Optional: search evidence attached to this news/article only",
    )
    limit: int = Field(default=10, ge=1, le=100)


class TextBody(BaseModel):
    text: str = Field(..., min_length=1, examples=["Alice Smith visited Paris on 2024-01-15."])


class MessageResponse(BaseModel):
    message: str


class RankedListResponse(BaseModel):
    actor: str
    results: list[dict[str, Any]] = []
