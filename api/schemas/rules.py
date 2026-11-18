"""Shared Pydantic field rules used across API schemas."""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator, Field, StringConstraints

from config.constants import ALLOWED_CONTENT_STATUSES, MIN_BODY_LENGTH, MIN_TITLE_LENGTH
from utils.errors import ValidationError as AppValidationError
from utils.validators import (
    ALLOWED_ARTICLE_TYPES,
    ALLOWED_PRIORITIES,
    ALLOWED_SEVERITIES,
    require_password,
)

UsernameStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=64),
]

# Login accepts any non-empty password (existing accounts may predate stricter rules).
LoginPasswordStr = Annotated[str, StringConstraints(min_length=1, max_length=128)]

TitleStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=MIN_TITLE_LENGTH, max_length=512),
]

BodyStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=MIN_BODY_LENGTH, max_length=50_000),
]

SummaryStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]


def _strong_password(value: str) -> str:
    try:
        return require_password(value)
    except AppValidationError as exc:
        raise ValueError(exc.message) from exc


StrongPasswordStr = Annotated[str, AfterValidator(_strong_password)]


def _content_status(value: str) -> str:
    text = (value or "").strip().lower()
    if text not in ALLOWED_CONTENT_STATUSES:
        raise ValueError(f"Invalid status. Allowed: {', '.join(ALLOWED_CONTENT_STATUSES)}")
    return text


def _severity(value: str) -> str:
    text = (value or "").strip().lower()
    if text not in ALLOWED_SEVERITIES:
        raise ValueError(f"Invalid severity. Allowed: {', '.join(ALLOWED_SEVERITIES)}")
    return text


def _article_type(value: str) -> str:
    text = (value or "").strip().lower()
    if text not in ALLOWED_ARTICLE_TYPES:
        raise ValueError(f"Invalid article_type. Allowed: {', '.join(ALLOWED_ARTICLE_TYPES)}")
    return text


def _priority(value: str) -> str:
    text = (value or "").strip().lower()
    if text not in ALLOWED_PRIORITIES:
        raise ValueError(f"Invalid priority. Allowed: {', '.join(ALLOWED_PRIORITIES)}")
    return text


ContentStatusStr = Annotated[str, AfterValidator(_content_status)]
SeverityStr = Annotated[str, AfterValidator(_severity)]
ArticleTypeStr = Annotated[str, AfterValidator(_article_type)]
PriorityStr = Annotated[str, AfterValidator(_priority)]

ScoreFloat = Annotated[float, Field(ge=0, le=1000)]
NonNegFloat = Annotated[float, Field(ge=0)]
