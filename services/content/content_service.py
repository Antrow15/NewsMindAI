"""Content domain service — news/article/pitch/category CRUD with validation."""

from __future__ import annotations

from typing import Any

from config.constants import ALLOWED_CONTENT_STATUSES
from dao.category_dao import CategoryDAO
from entities.content.article import Article
from entities.content.category import Category
from entities.content.content import Content
from entities.content.evidence import Evidence
from entities.content.news import News
from entities.content.story_pitch import StoryPitch
from repository.content_repository import ContentRepository
from utils.errors import NotFoundError, ValidationError
from utils.validators import (
    require_article_type,
    require_body,
    require_category_name,
    require_content_status,
    require_nonempty,
    require_optional_str,
    require_pitch_status,
    require_positive_id,
    require_priority,
    require_read_time,
    require_severity,
    require_title,
    validate_content_record,
)


class ContentService:
    def __init__(self, repo: ContentRepository | None = None) -> None:
        self.repo = repo or ContentRepository()
        self.categories = CategoryDAO()

    def add_category(self, name: str, description: str = "") -> int:
        return self.categories.create(
            Category(
                category_name=require_category_name(name),
                description=require_optional_str(description, "Description"),
            )
        )

    def add_pitch(self, title: str, summary: str, status: str = "submitted", priority: str = "medium") -> int:
        return self.repo.save_pitch(
            StoryPitch(
                title=require_title(title),
                summary=require_nonempty(summary, "Summary"),
                status=require_pitch_status(status),
                priority=require_priority(priority),
            )
        )

    def add_news(
        self,
        *,
        title: str,
        body: str,
        summary: str = "",
        event_title: str = "",
        event_type: str = "city",
        event_location: str = "",
        severity: str = "low",
        breaking: bool = False,
        status: str = "draft",
        author_id: int | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        status = require_content_status(status)
        title = require_title(title)
        body = require_body(body)
        items = list(evidence or [])
        if not items:
            raise ValidationError("At least one evidence item is required when creating news.")
        errors = validate_content_record(
            {"title": title, "text": body, "content_body": body, "status": status}
        )
        if errors:
            raise ValidationError(
                "Invalid news fields: "
                + ", ".join(errors)
                + f". Allowed status: {', '.join(ALLOWED_CONTENT_STATUSES)}."
            )
        content_id = self.repo.content.create(
            Content(
                author_id=author_id,
                title=title,
                summary=require_optional_str(summary, "Summary"),
                raw_body=body,
                content_body=body,
                status=status,
                content_kind="news",
                source_type="api",
            )
        )
        news_id = self.repo.news.create(
            News(
                content_id=content_id,
                event_title=require_optional_str(event_title, "Event title") or title,
                event_type=require_nonempty(event_type, "Event type"),
                event_location=require_optional_str(event_location, "Event location", max_len=255),
                severity=require_severity(severity),
                breaking_news_flag=bool(breaking),
            )
        )
        evidence_ids: list[int] = []
        for item in items:
            evidence_ids.append(
                self.add_evidence(
                    content_id=content_id,
                    title=str(item.get("title") or ""),
                    evidence_type=str(item.get("evidence_type") or "document"),
                    source_url=str(item.get("source_url") or ""),
                    text=str(item.get("text") or ""),
                    uploaded_by=author_id,
                )
            )
        return {"content_id": content_id, "news_id": news_id, "evidence_ids": evidence_ids}

    def add_article(
        self,
        *,
        title: str,
        body: str,
        summary: str = "",
        article_type: str = "feature",
        read_time: int = 3,
        status: str = "draft",
        author_id: int | None = None,
    ) -> dict[str, Any]:
        status = require_content_status(status)
        title = require_title(title)
        body = require_body(body)
        errors = validate_content_record(
            {"title": title, "text": body, "content_body": body, "status": status}
        )
        if errors:
            raise ValidationError("Invalid article fields: " + ", ".join(errors))
        content_id = self.repo.content.create(
            Content(
                author_id=author_id,
                title=title,
                summary=require_optional_str(summary, "Summary"),
                raw_body=body,
                content_body=body,
                status=status,
                content_kind="article",
                source_type="api",
            )
        )
        article_id = self.repo.articles.create(
            Article(
                content_id=content_id,
                article_type=require_article_type(article_type),
                estimated_read_time=require_read_time(read_time),
            )
        )
        return {"content_id": content_id, "article_id": article_id}

    def add_evidence(
        self,
        *,
        content_id: int,
        title: str,
        evidence_type: str = "document",
        source_url: str = "",
        text: str = "",
        uploaded_by: int | None = None,
    ) -> int:
        self.repo.get_content(content_id)
        return self.repo.save_evidence(
            Evidence(
                content_id=content_id,
                title=require_title(title),
                evidence_type=require_nonempty(evidence_type, "Evidence type"),
                source_url=require_optional_str(source_url, "Source URL"),
                body_text=require_optional_str(text, "Evidence text"),
                uploaded_by=uploaded_by,
            )
        )

    def get_content(self, content_id: int) -> dict[str, Any]:
        return self.repo.get_content(require_positive_id(content_id, "Content ID"))

    def get_content_by_input(self, raw_id: str) -> dict[str, Any]:
        return self.get_content(require_positive_id(raw_id, "Content ID"))

    def list_content(self, limit: int = 10, status: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        if status:
            return self.repo.content.list_by_status(require_content_status(status), limit=limit)
        return self.repo.content.list_all(limit=limit)

    def list_news(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.repo.news.list_all(limit=max(1, min(int(limit), 500)))

    def list_raw_ingest(self, limit: int = 15) -> list[dict[str, Any]]:
        return self.repo.raw.list_recent(limit=max(1, min(int(limit), 500)))

    def raw_ingest_counts(self) -> dict[str, int]:
        return self.repo.raw.count_by_status()

    def update_content_status(self, content_id: int, status: str) -> dict[str, Any]:
        content_id = require_positive_id(content_id, "Content ID")
        status = require_content_status(status)
        self.repo.get_content(content_id)
        changed = self.repo.content.update_status(content_id, status)
        if changed != 1:
            raise NotFoundError(f"Content ID {content_id} was not updated.")
        row = self.repo.get_content(content_id)
        return {"content_id": content_id, "status": row["status"], "title": row.get("title")}
