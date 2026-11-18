"""Journalist endpoint request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common import DocumentItem
from api.schemas.rules import (
    ArticleTypeStr,
    BodyStr,
    ContentStatusStr,
    SeverityStr,
    SummaryStr,
    TitleStr,
)

__all__ = [
    "DocumentItem",
    "DuplicatesRequest",
    "ValidateRequest",
    "RelatedContentRequest",
    "RelatedContentResponse",
    "CredibilityRequest",
    "PairsResponse",
    "ValidateResponse",
    "CredibilityResponse",
    "EvidenceItemIn",
    "NewsCreateRequest",
    "ArticleCreateRequest",
    "EvidenceCreateRequest",
    "ContentStatusRequest",
    "ContentCreateResponse",
    "ContentItemResponse",
    "ContentListResponse",
    "RawIngestListResponse",
    "EvidenceCreateResponse",
    "ContentStatusResponse",
]


class DuplicatesRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "documents": [
                        {"id": 1, "title": "A", "text": "same story about the city council"},
                        {"id": 2, "title": "B", "text": "same story about the city council"},
                    ],
                    "threshold": 0.5,
                    "limit": 10,
                }
            ]
        }
    )

    documents: list[DocumentItem] = Field(default_factory=list)
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    limit: int = Field(default=20, ge=1, le=100)


class ValidateRequest(BaseModel):
    title: str = ""
    text: str = ""
    status: str = "draft"
    category: str | None = None


class RelatedContentRequest(BaseModel):
    """While-typing related news via TF-IDF + cosine on published content."""

    title: str = ""
    text: str = ""
    limit: int = Field(default=8, ge=1, le=50)


class RelatedContentResponse(BaseModel):
    actor: str
    matches: list[dict[str, Any]] = Field(default_factory=list)
    relevancy: str = "none"
    best_score: float = 0.0
    corpus_size: int = 0
    knowledge_base_size: int = 0  # alias: published content count
    source: str = "content"
    method: str = "tfidf_cosine"


class CredibilityRequest(BaseModel):
    """Assess one news/article against the evidence already attached to it."""

    content_id: int = Field(..., gt=0)
    limit: int = Field(default=5, ge=1, le=50)


class PairsResponse(BaseModel):
    actor: str
    pairs: list[dict[str, Any]] = []


class ValidateResponse(BaseModel):
    actor: str
    ok: bool
    errors: list[str] = []
    title: str = ""
    relevancy: str | None = None
    relevancy_score: float | None = None
    relevancy_matches: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_base_size: int | None = None
    source: str | None = None


class CredibilityResponse(BaseModel):
    actor: str
    content_id: int
    evidence_count: int = 0
    claims: list[dict[str, Any]] = []
    summary: str = ""


class EvidenceItemIn(BaseModel):
    """Journalist-supplied evidence on news create (not from KB/datasets)."""

    title: TitleStr
    evidence_type: str = Field(default="document", min_length=2, max_length=64)
    source_url: str = Field(default="", max_length=1024)
    text: str = Field(default="", max_length=50_000, description="Optional plain body text")


class NewsCreateRequest(BaseModel):
    title: TitleStr
    body: BodyStr
    summary: SummaryStr = ""
    event_title: str = ""
    event_type: str = Field(default="city", min_length=2, max_length=64)
    event_location: str = Field(default="", max_length=255)
    severity: SeverityStr = "low"
    breaking: bool = False
    status: ContentStatusStr = "draft"
    evidence: list[EvidenceItemIn] = Field(..., min_length=1)


class ArticleCreateRequest(BaseModel):
    title: TitleStr
    body: BodyStr
    summary: SummaryStr = ""
    article_type: ArticleTypeStr = "feature"
    read_time: int = Field(default=3, ge=1, le=120)
    status: ContentStatusStr = "draft"
    evidence: list[EvidenceItemIn] = Field(..., min_length=1)


class EvidenceCreateRequest(BaseModel):
    content_id: int = Field(..., gt=0)
    title: TitleStr
    evidence_type: str = Field(default="document", min_length=2, max_length=64)
    source_url: str = Field(default="", max_length=1024)
    text: str = Field(default="", max_length=50_000)


class ContentStatusRequest(BaseModel):
    status: ContentStatusStr = Field(..., examples=["submitted"])


class ContentCreateResponse(BaseModel):
    actor: str
    content_id: int
    news_id: int | None = None
    article_id: int | None = None
    evidence_ids: list[int] = Field(default_factory=list)


class ContentItemResponse(BaseModel):
    actor: str
    content: dict[str, Any]


class ContentListResponse(BaseModel):
    actor: str
    items: list[dict[str, Any]] = []


class RawIngestListResponse(BaseModel):
    actor: str
    items: list[dict[str, Any]] = []
    counts: dict[str, int] = Field(default_factory=dict)


class EvidenceCreateResponse(BaseModel):
    actor: str
    evidence_id: int


class ContentStatusResponse(BaseModel):
    actor: str
    content_id: int
    status: str
    title: str | None = None
