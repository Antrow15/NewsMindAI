"""Content desk operations (news/article/pitch/category/list/view)."""

from __future__ import annotations

from typing import Any

from services.content import ContentService


class ContentModule:
    def __init__(self, service: ContentService | None = None) -> None:
        self.service = service or ContentService()

    def add_category(self, name: str, description: str = "") -> int:
        return self.service.add_category(name, description)

    def add_pitch(self, title: str, summary: str, status: str = "submitted") -> int:
        return self.service.add_pitch(title, summary, status=status)

    def add_news(self, **kwargs: Any) -> dict[str, Any]:
        return self.service.add_news(**kwargs)

    def add_article(self, **kwargs: Any) -> dict[str, Any]:
        return self.service.add_article(**kwargs)

    def list_content(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.service.list_content(limit=limit)

    def list_news(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.service.list_news(limit=limit)

    def list_raw(self, limit: int = 15) -> list[dict[str, Any]]:
        return self.service.list_raw_ingest(limit=limit)

    def raw_counts(self) -> dict[str, int]:
        return self.service.raw_ingest_counts()

    def get_content(self, content_id: int | str) -> dict[str, Any]:
        if isinstance(content_id, str):
            return self.service.get_content_by_input(content_id)
        return self.service.get_content(content_id)

    def update_status(self, content_id: int, status: str) -> dict[str, Any]:
        return self.service.update_content_status(content_id, status)
