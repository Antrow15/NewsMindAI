"""Content Adaptation Editor endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from api.deps import get_session_token
from api.http_errors import raise_http_error
from api.schemas.cae import (
    AdaptationCreate,
    AdaptationResponse,
    DraftResponse,
    FinalVersionRequest,
    RemarksRequest,
    RequiredRemarksRequest,
)
from config.constants import CAP_ADAPT
from services.access import require_capability_session
from services.adaptation import AdaptationService, ReviewService
from utils.errors import AuthError, NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/cae", tags=["4. Content Adaptation (CAE)"])
_adapt = AdaptationService()
_review = ReviewService()
_APP_ERRORS = (AuthError, PermissionDeniedError, ValidationError, NotFoundError)


def _user(token: str) -> dict[str, Any]:
    return require_capability_session(CAP_ADAPT, token)


def _draft_response(row: dict[str, Any]) -> DraftResponse:
    params = row.get("generation_parameters") or {}
    flags = row.get("validation_flags") or {}
    if isinstance(params, str):
        import json

        params = json.loads(params)
    if isinstance(flags, str):
        import json

        flags = json.loads(flags)
    return DraftResponse(
        id=int(row["id"]),
        platform=str(row["platform"]),
        version_number=int(row["version_number"]),
        adapted_title=str(row["adapted_title"]),
        adapted_content=str(row["adapted_content"]),
        model_version=str(row["model_version"]),
        status=str(row["status"]),
        generation_parameters=dict(params),
        validation_flags=dict(flags),
        created_at=row.get("created_at"),
    )


def _adaptation_response(payload: dict[str, Any]) -> AdaptationResponse:
    return AdaptationResponse(
        id=int(payload["id"]),
        original_title=str(payload["original_title"]),
        original_content=str(payload["original_content"]),
        created_by=payload.get("created_by"),
        status=str(payload["status"]),
        created_at=payload.get("created_at"),
        drafts=[_draft_response(d) for d in payload.get("drafts") or []],
    )


@router.post(
    "/adaptations",
    response_model=AdaptationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create adaptations",
)
def create_adaptation(body: AdaptationCreate, token: str = Depends(get_session_token)):
    try:
        user = _user(token)
        result = _adapt.create(
            original_title=body.original_title,
            original_content=body.original_content,
            target_platforms=body.target_platforms,
            created_by=int(user["user_id"]),
        )
        return _adaptation_response(result)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/adaptations/{request_id}",
    response_model=AdaptationResponse,
    summary="Get adaptation request",
)
def read_adaptation(request_id: int, token: str = Depends(get_session_token)):
    try:
        _user(token)
        return _adaptation_response(_adapt.get_request(request_id))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/adaptation-drafts/{draft_id}/approve",
    response_model=DraftResponse,
    summary="Approve draft",
)
def approve_draft(
    draft_id: int,
    body: RemarksRequest | None = None,
    token: str = Depends(get_session_token),
):
    try:
        user = _user(token)
        remarks = body.remarks if body else None
        return _draft_response(_review.approve(draft_id, int(user["user_id"]), remarks))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/adaptation-drafts/{draft_id}/reject",
    response_model=DraftResponse,
    summary="Reject draft",
)
def reject_draft(
    draft_id: int,
    body: RequiredRemarksRequest,
    token: str = Depends(get_session_token),
):
    try:
        user = _user(token)
        return _draft_response(_review.reject(draft_id, int(user["user_id"]), body.remarks))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/adaptation-drafts/{draft_id}/regenerate",
    response_model=DraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Regenerate draft",
)
def regenerate_draft(
    draft_id: int,
    body: RequiredRemarksRequest,
    token: str = Depends(get_session_token),
):
    try:
        user = _user(token)
        return _draft_response(
            _review.regenerate(draft_id, int(user["user_id"]), body.remarks)
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put(
    "/adaptation-drafts/{draft_id}/final",
    response_model=DraftResponse,
    summary="Finalize draft",
)
def finalize_draft(
    draft_id: int,
    body: FinalVersionRequest,
    token: str = Depends(get_session_token),
):
    try:
        user = _user(token)
        return _draft_response(
            _review.finalize(
                draft_id,
                int(user["user_id"]),
                body.final_title,
                body.final_content,
                body.remarks,
            )
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/adaptation-drafts/{draft_id}/versions",
    response_model=list[DraftResponse],
    summary="List draft versions",
)
def draft_versions(draft_id: int, token: str = Depends(get_session_token)):
    try:
        _user(token)
        return [_draft_response(row) for row in _review.versions(draft_id)]
    except _APP_ERRORS as exc:
        raise_http_error(exc)
