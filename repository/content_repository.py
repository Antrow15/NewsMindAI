"""Content-side repository: content, article, news, evidence, pitches, raw ingest."""

from __future__ import annotations

from typing import Any

from dao.article_dao import ArticleDAO
from dao.content_dao import ContentDAO
from dao.evidence_dao import EvidenceDAO
from dao.news_dao import NewsDAO
from dao.raw_ingest_dao import RawIngestDAO
from dao.story_pitch_dao import StoryPitchDAO
from entities.content.article import Article
from entities.content.content import Content
from entities.content.evidence import Evidence
from entities.content.news import News
from entities.content.story_pitch import StoryPitch


class ContentRepository:
    def __init__(self) -> None:
        self.content = ContentDAO()
        self.articles = ArticleDAO()
        self.news = NewsDAO()
        self.evidence = EvidenceDAO()
        self.pitches = StoryPitchDAO()
        self.raw = RawIngestDAO()

    def save_pitch(self, pitch: StoryPitch) -> int:
        return self.pitches.create(pitch)

    def save_content_bundle(self, content: Content, *, event_location: str = "") -> int:
        content_id = self.content.create(content)
        if (content.content_kind or "article") == "news":
            self.news.create(
                News(
                    content_id=content_id,
                    event_title=content.title,
                    event_location=event_location or None,
                )
            )
        else:
            self.articles.create(Article(content_id=content_id, article_type="feature"))
        return content_id

    def save_evidence(self, evidence: Evidence) -> int:
        return self.evidence.create(evidence)

    def get_content(self, content_id: int) -> dict[str, Any]:
        return self.content.require(content_id)
