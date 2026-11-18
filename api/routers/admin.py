"""Admin pipeline + user/category management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.deps import get_session_token
from api.http_errors import raise_http_error
from api.schemas.admin import (
    AddCategoryRequest,
    AddUserRequest,
    AdminActionResponse,
    CleanRequest,
    IngestFileRequest,
    IngestRequest,
    PersistRequest,
    PipelineRequest,
    ResetPasswordRequest,
)
from config.constants import CAP_ANALYTICS, CAP_MANAGE_USERS
from modules.admin import AdminModule
from services.access import require_capability_session
from services.content.content_service import ContentService
from services.user import UserService
from utils.errors import AuthError, NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/admin", tags=["8. Admin"])
_users = UserService()
_content = ContentService()
_APP_ERRORS = (AuthError, PermissionDeniedError, ValidationError, NotFoundError)


def _admin(token: str) -> AdminModule:
    return AdminModule(session_token=token)


def _ok(result: dict[str, Any], *, message: str = "") -> AdminActionResponse:
    return AdminActionResponse(message=message or str(result.get("message") or "OK"), result=result)


@router.get("/csv-files", response_model=AdminActionResponse, summary="List CSV files in data/raw")
def list_csv_files(token: str = Depends(get_session_token)):
    try:
        return _ok(_admin(token).list_csv_files())
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/ingest", response_model=AdminActionResponse, summary="Ingest CSV content")
def ingest(body: IngestRequest, token: str = Depends(get_session_token)):
    try:
        return _ok(_admin(token).ingest(only_new=body.only_new))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/ingest-file", response_model=AdminActionResponse, summary="Ingest one CSV file")
def ingest_file(body: IngestFileRequest, token: str = Depends(get_session_token)):
    try:
        return _ok(_admin(token).ingest_file(body.source_file))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/clean", response_model=AdminActionResponse, summary="Clean ingested data")
def clean(_body: CleanRequest, token: str = Depends(get_session_token)):
    try:
        return _ok(_admin(token).clean())
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/ingest-and-clean", response_model=AdminActionResponse, summary="Ingest then clean")
def ingest_and_clean(body: IngestRequest, token: str = Depends(get_session_token)):
    try:
        return _ok(_admin(token).ingest_and_clean(only_new=body.only_new))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/persist", response_model=AdminActionResponse, summary="Persist cleaned data")
def persist(_body: PersistRequest, token: str = Depends(get_session_token)):
    try:
        return _ok(_admin(token).persist())
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/pipeline", response_model=AdminActionResponse, summary="Full ETL pipeline")
def pipeline(body: PipelineRequest, token: str = Depends(get_session_token)):
    try:
        return _ok(_admin(token).run_pipeline(only_new=body.only_new))
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/users", response_model=AdminActionResponse, summary="Create user account")
def add_user(body: AddUserRequest, token: str = Depends(get_session_token)):
    try:
        result = _users.add_user(
            username=body.username,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
            email=body.email,
            role_code=body.role_code,
            employee_code=body.employee_code,
            session_token=token,
        )
        return AdminActionResponse(message=f"User {result['username']} created.", result=result)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/users/reset-password", response_model=AdminActionResponse, summary="Reset user password")
def reset_user_password(body: ResetPasswordRequest, token: str = Depends(get_session_token)):
    try:
        result = _users.reset_password(body.username, body.new_password, session_token=token)
        return AdminActionResponse(
            message=f"Password reset for {body.username}.",
            result=result,
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get(
    "/users/{username}",
    response_model=AdminActionResponse,
    summary="Look up user by username",
)
def get_user(username: str, token: str = Depends(get_session_token)):
    try:
        require_capability_session(CAP_MANAGE_USERS, token)
        result = _users.find_user(username)
        return AdminActionResponse(message="OK", result=result)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/categories", response_model=AdminActionResponse, summary="Add content category")
def add_category(body: AddCategoryRequest, token: str = Depends(get_session_token)):
    try:
        # Admin + newsroom manager (+ desks with analytics) may add categories
        require_capability_session(CAP_ANALYTICS, token)
        category_id = _content.add_category(body.name, body.description)
        return AdminActionResponse(
            message="Category created.",
            result={"category_id": category_id, "name": body.name},
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)