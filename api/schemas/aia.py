"""Audience Insight Analyst request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from api.schemas.rules import NonNegFloat, ScoreFloat, SummaryStr, TitleStr


class MetricsRequest(BaseModel):
    views: NonNegFloat = 120
    likes: NonNegFloat = 25
    shares: NonNegFloat = 8
    comments: NonNegFloat = 4


class EngagementResponse(BaseModel):
    engagement_score: float
    source: str | None = None
    raw: float | None = None
    features_used: list[str] | None = None


class InterestResponse(BaseModel):
    audience_interest_score: float
    source: str | None = None
    segment: int | None = None
    distance: float | None = None


class TrendRequest(BaseModel):
    title: TitleStr | None = None
    summary: SummaryStr = ""


class TrendResponse(BaseModel):
    trend_score: float
    source: str | None = None
    category: str | None = None
    category_confidence: float | None = None


class StoryPitchRequest(BaseModel):
    title: TitleStr
    summary: SummaryStr = Field(..., min_length=5)
    category: str = Field(..., min_length=2, max_length=64, description="Manual category (no model)")
    trend_score: ScoreFloat = 0.0
    audience_interest_score: ScoreFloat = 0.0
    coverage_gap_score: ScoreFloat = 0.0
    views: NonNegFloat = 120
    likes: NonNegFloat = 25
    shares: NonNegFloat = 8
    comments: NonNegFloat = 4


class StoryPitchResponse(BaseModel):
    story_pitch_id: int
    title: str
    summary: str
    pitch_importance: str
    priority: str | None = None  # same value; DB column name
    trend_score: float
    audience_interest_score: float
    coverage_gap_score: float
    importance_source: str | None = None
    source_type: str | None = None
    created_by_desk: str | None = None
    category: str | None = None


class StoryPitchListResponse(BaseModel):
    pitches: list[dict[str, Any]]


class PerformanceAnalyticsResponse(BaseModel):
    publication_by_status: dict[str, Any]
    content_by_status: dict[str, Any]
    pitch_outcomes: list[dict[str, Any]]
    pitches_by_source: dict[str, Any]
    recent_published: list[dict[str, Any]]
    insights: list[str]
    loop: str | None = None
