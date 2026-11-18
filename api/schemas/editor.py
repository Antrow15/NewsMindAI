"""Editor / newsroom manager schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from api.schemas.rules import SummaryStr, TitleStr


class RemarksBody(BaseModel):
    remarks: str = Field(default="", max_length=2000)


class AssignRequest(BaseModel):
    assignee_user_id: int = Field(..., gt=0)
    note: str = Field(default="", max_length=2000)


class PitchListResponse(BaseModel):
    pitches: list[dict[str, Any]]


class ContentListResponse(BaseModel):
    items: list[dict[str, Any]]


class UrgencyScoreRequest(BaseModel):
    """Score how urgent a story is for the editor review queue."""

    title: TitleStr
    summary: SummaryStr = ""


class UrgencyScoreResponse(BaseModel):
    urgency: str
    model_label: str | None = None
    confidence: float | None = None
    probabilities: dict[str, float] = Field(default_factory=dict)
    source: str


# Older names kept as aliases so imports do not break mid-edit
PriorityScoreRequest = UrgencyScoreRequest
PriorityScoreResponse = UrgencyScoreResponse


class EditorQueueResponse(BaseModel):
    tasks: list[dict[str, Any]]
    pitch_count: int
    content_count: int


class PitchDuplicateRequest(BaseModel):
    title: TitleStr | None = None
    summary: SummaryStr = ""
    status: str = "submitted"
    threshold: float = Field(default=0.45, ge=0.1, le=0.95)


class PitchDuplicateResponse(BaseModel):
    query_title: str | None = None
    matches: list[dict[str, Any]] | None = None
    match_count: int | None = None
    pairs: list[dict[str, Any]] | None = None
    pair_count: int | None = None
    scanned: int


class SuggestJournalistRequest(BaseModel):
    topic: str = ""
    title: TitleStr | None = None
    limit: int = Field(default=10, ge=1, le=50)


class SuggestJournalistResponse(BaseModel):
    suggestions: list[dict[str, Any]]
    topic: str | None = None
    method: str | None = None


class ManagerOverviewResponse(BaseModel):
    submitted_pitches: int
    submitted_content: int
    approved_content: int
    publication: dict[str, Any]


class BottlenecksResponse(BaseModel):
    content_stages: list[dict[str, Any]]
    pitch_stages: list[dict[str, Any]]
    publication_stages: list[dict[str, Any]]
    adaptation_stages: list[dict[str, Any]]
    hotspots: list[dict[str, Any]]


class BusinessAnalyticsResponse(BaseModel):
    pipeline: dict[str, Any]
    ops: dict[str, Any]
    bottleneck_hotspots: list[dict[str, Any]]
    workload_summary: dict[str, Any] | None = None
    deadline_risk_summary: dict[str, Any] | None = None
    resource_summary: dict[str, Any] | None = None
    totals: dict[str, Any]


class WorkloadResponse(BaseModel):
    journalists: list[dict[str, Any]]
    total_open_items: int
    method: str | None = None


class DeadlineRiskResponse(BaseModel):
    thresholds_hours: dict[str, Any]
    content_at_risk: list[dict[str, Any]]
    pitches_at_risk: list[dict[str, Any]]
    at_risk_count: int
    method: str | None = None


class ResourcesResponse(BaseModel):
    desks: list[dict[str, Any]]
    utilization: dict[str, Any]
    overloaded: list[dict[str, Any]]
    underutilized: list[dict[str, Any]]
    method: str | None = None

