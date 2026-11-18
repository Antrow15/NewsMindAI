"""Compatibility façade over ContentRepository + UserRepository."""

from __future__ import annotations

from typing import Any

from entities.content.content import Content
from entities.content.evidence import Evidence
from entities.content.story_pitch import StoryPitch
from repository.content_repository import ContentRepository
from repository.user_repository import UserRepository


class NewsroomRepository:
    """Thin façade kept for older call sites; prefer Content/User repositories."""

    def __init__(self) -> None:
        self.content_repo = ContentRepository()
        self.user_repo = UserRepository()
        self.users = self.user_repo.users
        self.journalists = self.user_repo.journalists
        self.editors = self.user_repo.editors
        self.analysts = self.user_repo.analysts
        self.adapters = self.user_repo.adapters
        self.publishers = self.user_repo.publishers
        self.managers = self.user_repo.managers
        self.pitches = self.content_repo.pitches
        self.content = self.content_repo.content
        self.articles = self.content_repo.articles
        self.news = self.content_repo.news
        self.evidence = self.content_repo.evidence

    def ensure_demo_user(self, username: str = "journalist") -> dict[str, Any]:
        return self.user_repo.ensure_demo_user(username)

    def get_profile_ids(self, user_id: int) -> dict[str, Any]:
        return self.user_repo.get_profile_ids(user_id)

    def save_pitch(self, pitch: StoryPitch) -> int:
        return self.content_repo.save_pitch(pitch)

    def save_content_bundle(self, content: Content, *, event_location: str = "") -> int:
        return self.content_repo.save_content_bundle(content, event_location=event_location)

    def save_evidence(self, evidence: Evidence) -> int:
        return self.content_repo.save_evidence(evidence)
