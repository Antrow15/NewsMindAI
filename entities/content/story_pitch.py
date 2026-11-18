"""Content pipeline: StoryPitch."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class StoryPitch:
    story_pitch_id: Optional[int] = None
    audience_insight_id: Optional[int] = None
    title: str = ""
    summary: Optional[str] = None
    priority: str = "medium"
    source_type: Optional[str] = None
    trend_score: float = 0.0
    audience_interest_score: float = 0.0
    coverage_gap_score: float = 0.0
    status: str = "submitted"
    created_by: Optional[int] = None
    approved_by: Optional[int] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
