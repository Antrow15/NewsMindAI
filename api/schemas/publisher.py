"""Publisher request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TemplateAssignRequest(BaseModel):
    template_code: str = Field(..., min_length=2, max_length=64)


class ScheduleRequest(BaseModel):
    scheduled_at: datetime


class ArticlesResponse(BaseModel):
    articles: list[dict[str, Any]]


class TemplatesResponse(BaseModel):
    templates: list[dict[str, Any]]


class PublicationActionResponse(BaseModel):
    content_id: int
    publication: dict[str, Any]


class PreviewResponse(BaseModel):
    content_id: int
    title: str | None = None
    template: dict[str, Any]
    preview_html: str
    publication_status: str | None = None


class AnalyticsResponse(BaseModel):
    approved_content: int
    publications_by_status: dict[str, int]
    published: int
    scheduled: int
    ready: int
    approved: int
