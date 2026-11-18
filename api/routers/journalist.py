"""Journalist tools + desk content endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.deps import get_session_token
from api.http_errors import raise_http_error
from api.schemas.journalist import (
    ArticleCreateRequest,
    ContentCreateResponse,
    ContentItemResponse,
    ContentListResponse,
    ContentStatusRequest,
    ContentStatusResponse,
    CredibilityRequest,
    CredibilityResponse,
    DuplicatesRequest,
    EntitiesResponse,
    EvidenceCreateRequest,
    EvidenceCreateResponse,
    NewsCreateRequest,
    PairsResponse,
    PatentSearchRequest,
    RankedListResponse,
    RawIngestListResponse,
    RelatedContentRequest,
    RelatedContentResponse,
    SearchRequest,
    TextBody,
    ValidateRequest,
    ValidateResponse,
)
from modules.journalist import JournalistModule
from utils.errors import AuthError, NotFoundError, PermissionDeniedError, ValidationError

router = APIRouter(prefix="/journalist", tags=["2. Journalist tools"])

_APP_ERRORS = (AuthError, PermissionDeniedError, ValidationError, NotFoundError)


def _tools(token: str) -> JournalistModule:
    return JournalistModule(session_token=token)


def _as_dicts(items) -> list[dict]:
    return [item.model_dump() for item in items]


# ── AI tools ─────────────────────────────────────────────────────────────────


@router.post("/research", response_model=RankedListResponse, summary="Research related news")
def research(body: SearchRequest, token: str = Depends(get_session_token)):
    try:
        return _tools(token).research(body.query, _as_dicts(body.documents), limit=body.limit)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/evidence-search", response_model=RankedListResponse, summary="Search evidence")
def evidence_search(body: SearchRequest, token: str = Depends(get_session_token)):
    try:
        return _tools(token).evidence_search(
            body.query, _as_dicts(body.documents), limit=body.limit
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/metadata", response_model=EntitiesResponse, summary="Extract metadata")
def metadata(body: TextBody, token: str = Depends(get_session_token)):
    try:
        return _tools(token).metadata(body.text)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/duplicates", response_model=PairsResponse, summary="Find duplicates")
def duplicates(body: DuplicatesRequest, token: str = Depends(get_session_token)):
    try:
        return _tools(token).duplicates(
            _as_dicts(body.documents),
            threshold=body.threshold,
            limit=body.limit,
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/validate", response_model=ValidateResponse, summary="Validate article fields")
def validate(body: ValidateRequest, token: str = Depends(get_session_token)):
    try:
        return _tools(token).validate(body.model_dump())
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post(
    "/related-content",
    response_model=RelatedContentResponse,
    summary="Related news from knowledge base (while-typing API)",
)
def related_content(body: RelatedContentRequest, token: str = Depends(get_session_token)):
    try:
        return _tools(token).related_content(
            title=body.title,
            text=body.text,
            limit=body.limit,
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/credibility", response_model=CredibilityResponse, summary="Assess credibility")
def credibility(body: CredibilityRequest, token: str = Depends(get_session_token)):
    try:
        return _tools(token).credibility(
            body.text,
            _as_dicts(body.evidence_docs),
            limit=body.limit,
        )
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/patents", response_model=RankedListResponse, summary="Search patents")
def patents(body: PatentSearchRequest, token: str = Depends(get_session_token)):
    try:
        docs = None if body.documents is None else _as_dicts(body.documents)
        return _tools(token).patents(body.query, docs, limit=body.limit)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


# ── Desk content (console parity) ─────────────────────────────────────────────


@router.post("/news", response_model=ContentCreateResponse, summary="Add news")
def add_news(body: NewsCreateRequest, token: str = Depends(get_session_token)):
    try:
        return _tools(token).add_news(**body.model_dump())
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/articles", response_model=ContentCreateResponse, summary="Add article")
def add_article(body: ArticleCreateRequest, token: str = Depends(get_session_token)):
    try:
        return _tools(token).add_article(**body.model_dump())
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get("/content", response_model=ContentListResponse, summary="List content")
def list_content(
    limit: int = Query(default=20, ge=1, le=500),
    status: str | None = Query(default=None, description="Filter e.g. rework, submitted"),
    token: str = Depends(get_session_token),
):
    try:
        return _tools(token).list_content(limit=limit, status=status)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get("/content/{content_id}", response_model=ContentItemResponse, summary="View content")
def get_content(content_id: int, token: str = Depends(get_session_token)):
    try:
        return _tools(token).get_content(content_id)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.put(
    "/content/{content_id}/status",
    response_model=ContentStatusResponse,
    summary="Update content status",
)
def update_content_status(
    content_id: int,
    body: ContentStatusRequest,
    token: str = Depends(get_session_token),
):
    try:
        return _tools(token).update_content_status(content_id, body.status)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get("/news", response_model=ContentListResponse, summary="List news")
def list_news(
    limit: int = Query(default=20, ge=1, le=500),
    token: str = Depends(get_session_token),
):
    try:
        return _tools(token).list_news(limit=limit)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.get("/raw-ingest", response_model=RawIngestListResponse, summary="List raw ingest")
def list_raw_ingest(
    limit: int = Query(default=20, ge=1, le=500),
    token: str = Depends(get_session_token),
):
    try:
        return _tools(token).list_raw_ingest(limit=limit)
    except _APP_ERRORS as exc:
        raise_http_error(exc)


@router.post("/evidence", response_model=EvidenceCreateResponse, summary="Add evidence")
def add_evidence(body: EvidenceCreateRequest, token: str = Depends(get_session_token)):
    try:
        return _tools(token).add_evidence(**body.model_dump())
    except _APP_ERRORS as exc:
        raise_http_error(exc)
