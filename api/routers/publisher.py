"""Publisher endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_session_token
from api.http_errors import raise_http_error
from api.schemas.publisher import (
    AnalyticsResponse,
    ArticlesResponse,
    PreviewResponse,
    PublicationActionResponse,
    ScheduleRequest,
    TemplateAssignRequest,
    TemplatesResponse,
)
from config.constants import CAP_PUBLISH
from services.access import require_capability_session
from services.publisher import PublisherService
from utils.errors import AuthError, NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/publisher", tags=["5. Publisher"])
_service = PublisherService()
_APP_ERRORS = (AuthError, PermissionDeniedError, ValidationError, NotFoundError)


def _require(token: str) -> None:
    require_capability_session(CAP_PUBLISH, token)


@router.get("/articles", response_model=ArticlesResponse, summary="Ready articles")
def list_articles(token: str = Depends(get_session_token)):
    try:
        _require(token)
        return _service.list_articles()
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put(
    "/articles/{content_id}/approve",
    response_model=PublicationActionResponse,
    summary="Approve for publication",
)
def approve_article(content_id: int, token: str = Depends(get_session_token)):
    try:
        _require(token)
        return _service.approve(content_id)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get("/templates", response_model=TemplatesResponse, summary="Publication templates")
def list_templates(token: str = Depends(get_session_token)):
    try:
        _require(token)
        return _service.templates()
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put(
    "/articles/{content_id}/template",
    response_model=PublicationActionResponse,
    summary="Assign template",
)
def assign_template(
    content_id: int,
    body: TemplateAssignRequest,
    token: str = Depends(get_session_token),
):
    try:
        _require(token)
        return _service.assign_template(content_id, body.template_code)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/articles/{content_id}/preview",
    response_model=PreviewResponse,
    summary="Preview article",
)
def preview_article(content_id: int, token: str = Depends(get_session_token)):
    try:
        _require(token)
        return _service.preview(content_id)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/articles/{content_id}/publish",
    response_model=PublicationActionResponse,
    summary="Publish now",
)
def publish_article(content_id: int, token: str = Depends(get_session_token)):
    try:
        _require(token)
        return _service.publish(content_id)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/articles/{content_id}/schedule",
    response_model=PublicationActionResponse,
    summary="Schedule publication",
)
def schedule_article(
    content_id: int,
    body: ScheduleRequest,
    token: str = Depends(get_session_token),
):
    try:
        _require(token)
        return _service.schedule(content_id, body.scheduled_at)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get("/analytics", response_model=AnalyticsResponse, summary="Publication analytics")
def analytics(token: str = Depends(get_session_token)):
    try:
        _require(token)
        return _service.analytics()
    except _APP_ERRORS as exc:
        raise_http_error(exc)
