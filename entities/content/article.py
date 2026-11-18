"""Content pipeline: Article (specializes Content)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Article:
    article_id: Optional[int] = None
    content_id: Optional[int] = None
    story_pitch_id: Optional[int] = None
    article_type: str = "feature"
    estimated_read_time: Optional[int] = None
