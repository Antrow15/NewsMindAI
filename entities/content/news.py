"""Content pipeline: News (specializes Content)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class News:
    news_id: Optional[int] = None
    content_id: Optional[int] = None
    event_title: Optional[str] = None
    event_type: Optional[str] = None
    event_location: Optional[str] = None
    event_date: Optional[datetime] = None
    breaking_news_flag: bool = False
    severity: Optional[str] = None
