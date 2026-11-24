"""Editor desk endpoints — queue ordered by editor_queue_urgency model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from api.deps import get_session_token
from api.http_errors import raise_http_error
from api.schemas.editor import (
    AssignRequest,
    ContentListResponse,
    EditorCreateAssignRequest,
    EditorQueueResponse,
    PitchAssignRequest,
    PitchDuplicateRequest,
    PitchDuplicateResponse,
    PitchListResponse,
    RemarksBody,
    SuggestJournalistRequest,
    SuggestJournalistResponse,
    UrgencyScoreRequest,
    UrgencyScoreResponse,
)
from config.constants import CAP_ASSIGN, CAP_CONTENT_REVIEW, CAP_PITCH_REVIEW
from services.access import require_capability_session
from services.editor import EditorService
from utils.errors import AuthError, NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/editor", tags=["6. Editor"])
_service = EditorService()
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


@router.get(
    "/queue",
    response_model=EditorQueueResponse,
    summary="Priority review queue (urgent/high first)",
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


@router.post(
    "/queue/score",
    response_model=UrgencyScoreResponse,
    summary="Score editor-queue urgency (urgent/high/medium/low)",
)
def score_queue_urgency(body: UrgencyScoreRequest, token: str = Depends(get_session_token)):
    try:
        _user(token, CAP_PITCH_REVIEW)
        return _service.score_editor_queue_urgency(body.title, body.summary)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get("/pitches", response_model=PitchListResponse, summary="List pitches")
def list_pitches(
    status: str = Query(default="submitted"),
    token: str = Depends(get_session_token),
):
    try:
        _user(token, CAP_PITCH_REVIEW)
        return _service.list_pitches(status=status)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/pitches/duplicates",
    response_model=PitchDuplicateResponse,
    summary="Detect duplicate story pitches (shows AIA vs manual)",
)
def pitch_duplicates(
    body: PitchDuplicateRequest | None = None,
    token: str = Depends(get_session_token),
):
    try:
        _user(token, CAP_PITCH_REVIEW)
        payload = body or PitchDuplicateRequest()
        return _service.find_duplicate_pitches(
            title=payload.title,
            summary=payload.summary or "",
            status=payload.status,
            threshold=payload.threshold,
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/assign/suggest",
    response_model=SuggestJournalistResponse,
    summary="Suggest journalist by specialty + workload",
)
def suggest_journalist(body: SuggestJournalistRequest, token: str = Depends(get_session_token)):
    try:
        _user(token, CAP_ASSIGN)
        return _service.suggest_journalists(
            topic=body.topic,
            title=body.title or "",
            limit=body.limit,
        )
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
        remarks = body.remarks if body else ""
        return _service.reject_pitch(story_pitch_id, remarks=remarks)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/content",
    response_model=ContentListResponse,
    summary="List content for review (model priority order)",
)
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
        remarks = body.remarks if body else ""
        return _service.reject_content(content_id, remarks=remarks)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put(
    "/content/{content_id}/rework",
    summary="Send content back for rework",
)
def rework_content(
    content_id: int,
    body: RemarksBody | None = None,
    token: str = Depends(get_session_token),
):
    try:
        _user(token, CAP_CONTENT_REVIEW)
        remarks = body.remarks if body else ""
        return _service.send_content_rework(content_id, remarks=remarks)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/content/create-assign",
    summary="Create news/article and assign journalist",
)
def create_and_assign(
    body: EditorCreateAssignRequest,
    token: str = Depends(get_session_token),
):
    try:
        user = _user(token, CAP_ASSIGN)
        return _service.create_and_assign(
            kind=body.kind,
            title=body.title,
            body=body.body,
            summary=body.summary,
            assignee_user_id=body.assignee_user_id,
            assigner_user_id=int(user["user_id"]),
            note=body.note,
            due_at=_parse_due(body.due_at),
            event_type=body.event_type,
            event_location=body.event_location,
            severity=body.severity,
            breaking=body.breaking,
            article_type=body.article_type,
            read_time=body.read_time,
            evidence_title=body.evidence_title,
        )
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
