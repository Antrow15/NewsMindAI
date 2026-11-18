"""Audience Insight Analyst endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_session_token
from api.http_errors import raise_http_error
from api.schemas.aia import (
    EngagementResponse,
    InterestResponse,
    MetricsRequest,
    PerformanceAnalyticsResponse,
    StoryPitchListResponse,
    StoryPitchRequest,
    StoryPitchResponse,
    TrendRequest,
    TrendResponse,
)
from config.constants import CAP_ANALYTICS
from services.access import require_capability_session
from services.aia import AIAService
from utils.errors import AuthError, NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/aia", tags=["3. Audience Insight Analyst"])
_service = AIAService()
_APP_ERRORS = (AuthError, PermissionDeniedError, ValidationError, NotFoundError)


def _require_aia(token: str) -> None:
    require_capability_session(CAP_ANALYTICS, token)


@router.post("/analyze-engagement", response_model=EngagementResponse, summary="Analyze engagement")
def analyze_engagement(
    body: MetricsRequest | None = None,
    token: str = Depends(get_session_token),
):
    try:
        _require_aia(token)
        metrics = body or MetricsRequest()
        return _service.analyze_engagement(
            views=metrics.views,
            likes=metrics.likes,
            shares=metrics.shares,
            comments=metrics.comments,
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/analyze-interest", response_model=InterestResponse, summary="Analyze interest")
def analyze_interest(
    body: MetricsRequest | None = None,
    token: str = Depends(get_session_token),
):
    try:
        _require_aia(token)
        metrics = body or MetricsRequest()
        return _service.analyze_interest(
            views=metrics.views,
            likes=metrics.likes,
            shares=metrics.shares,
            comments=metrics.comments,
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/analyze-trends", response_model=TrendResponse, summary="Analyze trends")
def analyze_trends(
    body: TrendRequest | None = None,
    token: str = Depends(get_session_token),
):
    try:
        _require_aia(token)
        payload = body or TrendRequest()
        return _service.analyze_trends(payload.title or "", payload.summary or "")
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/performance",
    response_model=PerformanceAnalyticsResponse,
    summary="Performance analytics loop (publication → AIA)",
)
def performance_analytics(token: str = Depends(get_session_token)):
    try:
        _require_aia(token)
        return _service.performance_analytics()
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/generate-story-pitch",
    response_model=StoryPitchResponse,
    summary="Generate story pitch",
)
def generate_story_pitch(
    body: StoryPitchRequest,
    token: str = Depends(get_session_token),
):
    try:
        _require_aia(token)
        return _service.generate_story_pitch(body)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get("/story-pitches", response_model=StoryPitchListResponse, summary="List story pitches")
def get_story_pitches(token: str = Depends(get_session_token)):
    try:
        _require_aia(token)
        return _service.get_story_pitches()
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/story-pitches/top",
    response_model=StoryPitchListResponse,
    summary="Top story pitches",
)
def get_top_story_pitches(token: str = Depends(get_session_token)):
    try:
        _require_aia(token)
        return _service.get_top_story_pitches()
    except _APP_ERRORS as exc:
        raise_http_error(exc)
