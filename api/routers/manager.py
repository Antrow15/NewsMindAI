"""Newsroom manager endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from api.deps import get_session_token
from api.http_errors import raise_http_error
from api.schemas.editor import (
    AssignRequest,
    BottlenecksResponse,
    BusinessAnalyticsResponse,
    ContentListResponse,
    DeadlineRiskResponse,
    EditorQueueResponse,
    ManagerOverviewResponse,
    PitchAssignRequest,
    PitchListResponse,
    RemarksBody,
    ResourcesResponse,
    WorkloadResponse,
)
from config.constants import CAP_ANALYTICS, CAP_ASSIGN, CAP_CONTENT_REVIEW, CAP_PITCH_REVIEW
from services.access import require_capability_session
from services.manager import ManagerService
from utils.errors import AuthError, NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/manager", tags=["7. Newsroom Manager"])
_service = ManagerService()
_APP_ERRORS = (AuthError, PermissionDeniedError, ValidationError, NotFoundError)


def _user(token: str, capability: str) -> dict[str, Any]:
    return require_capability_session(capability, token)


def _parse_due(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError("due_at must be an ISO datetime.") from exc


@router.get("/overview", response_model=ManagerOverviewResponse, summary="Desk overview")
def overview(token: str = Depends(get_session_token)):
    try:
        # Manager needs at least one of the desk capabilities; pitch_review is common.
        _user(token, CAP_PITCH_REVIEW)
        return _service.overview()
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/bottlenecks",
    response_model=BottlenecksResponse,
    summary="Pipeline bottleneck analysis",
)
def bottlenecks(token: str = Depends(get_session_token)):
    try:
        _user(token, CAP_ANALYTICS)
        return _service.bottlenecks()
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/analytics",
    response_model=BusinessAnalyticsResponse,
    summary="Whole-application business analytics",
)
def business_analytics(token: str = Depends(get_session_token)):
    try:
        _user(token, CAP_ANALYTICS)
        return _service.business_analytics()
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/workload",
    response_model=WorkloadResponse,
    summary="Journalist workload analysis",
)
def workload(token: str = Depends(get_session_token)):
    try:
        _user(token, CAP_ANALYTICS)
        return _service.workload()
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/deadline-risk",
    response_model=DeadlineRiskResponse,
    summary="Deadline risk from time stuck in stage",
)
def deadline_risk(
    submitted_hours: float = Query(default=48.0, ge=1.0, le=720.0),
    rework_hours: float = Query(default=24.0, ge=1.0, le=720.0),
    token: str = Depends(get_session_token),
):
    try:
        _user(token, CAP_ANALYTICS)
        return _service.deadline_risk(
            submitted_hours=submitted_hours,
            rework_hours=rework_hours,
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/resources",
    response_model=ResourcesResponse,
    summary="Resource utilization across desks",
)
def resources(token: str = Depends(get_session_token)):
    try:
        _user(token, CAP_ANALYTICS)
        return _service.resources()
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/queue",
    response_model=EditorQueueResponse,
    summary="Priority review queue (same as Editor)",
)
def review_queue(
    pitch_status: str = Query(default="submitted"),
    content_status: str = Query(default="submitted"),
    token: str = Depends(get_session_token),
):
    try:
        _user(token, CAP_PITCH_REVIEW)
        return _service.review_queue(
            pitch_status=pitch_status,
            content_status=content_status,
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get("/pitches", response_model=PitchListResponse, summary="List pitches (priority order)")
def list_pitches(
    status: str = Query(default="submitted"),
    token: str = Depends(get_session_token),
):
    try:
        _user(token, CAP_PITCH_REVIEW)
        return _service.list_pitches(status=status)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put("/pitches/{story_pitch_id}/approve", summary="Approve pitch")
def approve_pitch(story_pitch_id: int, token: str = Depends(get_session_token)):
    try:
        user = _user(token, CAP_PITCH_REVIEW)
        return _service.approve_pitch(story_pitch_id, int(user["user_id"]))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put("/pitches/{story_pitch_id}/reject", summary="Reject pitch")
def reject_pitch(
    story_pitch_id: int,
    body: RemarksBody | None = None,
    token: str = Depends(get_session_token),
):
    try:
        _user(token, CAP_PITCH_REVIEW)
        return _service.reject_pitch(story_pitch_id, remarks=(body.remarks if body else ""))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get("/content", response_model=ContentListResponse, summary="List content")
def list_content(
    status: str = Query(default="submitted"),
    token: str = Depends(get_session_token),
):
    try:
        _user(token, CAP_CONTENT_REVIEW)
        return _service.list_content(status=status)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put("/content/{content_id}/approve", summary="Approve content")
def approve_content(content_id: int, token: str = Depends(get_session_token)):
    try:
        _user(token, CAP_CONTENT_REVIEW)
        return _service.approve_content(content_id)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put("/content/{content_id}/reject", summary="Reject content")
def reject_content(
    content_id: int,
    body: RemarksBody | None = None,
    token: str = Depends(get_session_token),
):
    try:
        _user(token, CAP_CONTENT_REVIEW)
        return _service.reject_content(content_id, remarks=(body.remarks if body else ""))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put("/content/{content_id}/assign", summary="Assign content")
def assign_content(
    content_id: int,
    body: AssignRequest,
    token: str = Depends(get_session_token),
):
    try:
        user = _user(token, CAP_ASSIGN)
        return _service.assign_content(
            content_id,
            body.assignee_user_id,
            note=body.note,
            due_at=_parse_due(body.due_at),
            assigner_user_id=int(user["user_id"]),
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/pitches/{story_pitch_id}/assign",
    summary="Assign approved pitch to journalist (creates draft article)",
)
def assign_pitch(
    story_pitch_id: int,
    body: PitchAssignRequest,
    token: str = Depends(get_session_token),
):
    try:
        user = _user(token, CAP_ASSIGN)
        return _service.assign_pitch(
            story_pitch_id,
            body.assignee_user_id,
            assigner_user_id=int(user["user_id"]),
            note=body.note,
            due_at=_parse_due(body.due_at),
            auto_approve=body.auto_approve,
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)
