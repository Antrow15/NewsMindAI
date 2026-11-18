"""Field validation used by DAOs, services, and cleaners."""

from __future__ import annotations

import re
from typing import Any, Optional

from config.constants import (
    ALLOWED_ACCOUNT_STATUSES,
    ALLOWED_CONTENT_STATUSES,
    ALLOWED_PITCH_STATUSES,
    CONTENT_KINDS,
    MIN_BODY_LENGTH,
    MIN_TITLE_LENGTH,
)
from utils.errors import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_SEVERITIES = ("low", "medium", "high", "critical")
ALLOWED_PRIORITIES = ("low", "medium", "high", "urgent")
ALLOWED_ARTICLE_TYPES = ("feature", "analysis", "opinion", "profile", "explainer")
ALLOWED_DESK_STATUSES = ("active", "inactive")
ALLOWED_AVAILABILITY = ("available", "busy", "away", "leave")
ALLOWED_EMPLOYMENT = ("active", "inactive", "terminated")
ALLOWED_CLEANING_STATUS = ("pending", "kept", "rejected", "ingested")


def is_nonempty(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def require_nonempty(value: Any, label: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValidationError(f"{label} cannot be empty.")
    return text


def require_optional_str(value: Any, label: str, *, max_len: Optional[int] = None) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if max_len is not None and len(text) > max_len:
        raise ValidationError(f"{label} must be at most {max_len} characters.")
    return text


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match((value or "").strip()))


def require_email(value: Any) -> str:
    email = require_nonempty(value, "Email")
    if not is_valid_email(email):
        raise ValidationError("A valid email is required.")
    return email


def is_valid_title(value: str) -> bool:
    return len((value or "").strip()) >= MIN_TITLE_LENGTH


def require_title(value: Any) -> str:
    title = require_nonempty(value, "Title")
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError(f"Title must be at least {MIN_TITLE_LENGTH} characters.")
    if len(title) > 512:
        raise ValidationError("Title must be at most 512 characters.")
    return title


def is_valid_body(value: str, *, headline_ok: bool = False) -> bool:
    text = (value or "").strip()
    if len(text) >= MIN_BODY_LENGTH:
        return True
    if headline_ok and len(text) >= MIN_TITLE_LENGTH:
        return True
    return False


def require_body(value: Any, *, headline_ok: bool = False) -> str:
    body = require_nonempty(value, "Body")
    if not is_valid_body(body, headline_ok=headline_ok):
        raise ValidationError(f"Body must be at least {MIN_BODY_LENGTH} characters.")
    return body


def require_choice(value: Any, label: str, allowed: tuple[str, ...]) -> str:
    text = require_nonempty(value, label).lower()
    if text not in {a.lower() for a in allowed}:
        raise ValidationError(f"Invalid {label.lower()} '{value}'. Allowed: {', '.join(allowed)}")
    return text


def is_allowed_content_status(value: str) -> bool:
    return (value or "").strip().lower() in ALLOWED_CONTENT_STATUSES


def is_allowed_pitch_status(value: str) -> bool:
    return (value or "").strip().lower() in ALLOWED_PITCH_STATUSES


def is_allowed_account_status(value: str) -> bool:
    return (value or "").strip().lower() in ALLOWED_ACCOUNT_STATUSES


def is_allowed_content_kind(value: str) -> bool:
    return (value or "").strip().lower() in CONTENT_KINDS


def require_content_status(value: str) -> str:
    return require_choice(value if value is not None else "", "Status", ALLOWED_CONTENT_STATUSES)


def require_pitch_status(value: str) -> str:
    return require_choice(value if value is not None else "", "Status", ALLOWED_PITCH_STATUSES)


def require_account_status(value: str) -> str:
    return require_choice(value if value is not None else "", "Account status", ALLOWED_ACCOUNT_STATUSES)


def require_content_kind(value: str) -> str:
    return require_choice(value if value is not None else "", "Content kind", CONTENT_KINDS)


def require_severity(value: Any) -> str:
    return require_choice(value if value is not None else "", "Severity", ALLOWED_SEVERITIES)


def require_priority(value: Any) -> str:
    return require_choice(value if value is not None else "", "Priority", ALLOWED_PRIORITIES)


def require_article_type(value: Any) -> str:
    return require_choice(value if value is not None else "", "Article type", ALLOWED_ARTICLE_TYPES)


def require_desk_status(value: Any) -> str:
    return require_choice(value if value is not None else "", "Status", ALLOWED_DESK_STATUSES)


def require_availability(value: Any) -> str:
    return require_choice(value if value is not None else "", "Availability", ALLOWED_AVAILABILITY)


def require_employment_status(value: Any) -> str:
    return require_choice(value if value is not None else "", "Employment status", ALLOWED_EMPLOYMENT)


def require_cleaning_status(value: Any) -> str:
    return require_choice(value if value is not None else "", "Cleaning status", ALLOWED_CLEANING_STATUS)


def require_positive_id(raw: Any, label: str = "ID") -> int:
    if isinstance(raw, int):
        value = raw
    else:
        text = "" if raw is None else str(raw).strip()
        if not text:
            raise ValidationError(f"{label} cannot be empty.")
        try:
            value = int(text)
        except ValueError as exc:
            raise ValidationError(f"{label} must be a number.") from exc
    if value <= 0:
        raise ValidationError(f"{label} must be a positive number.")
    return value


def require_optional_positive_id(raw: Any, label: str = "ID") -> Optional[int]:
    if raw is None or str(raw).strip() == "":
        return None
    return require_positive_id(raw, label)


def require_username(value: Any) -> str:
    username = require_nonempty(value, "Username")
    if len(username) < 3:
        raise ValidationError("Username must be at least 3 characters.")
    if " " in username:
        raise ValidationError("Username cannot contain spaces.")
    return username


_PASSWORD_RULES = (
    (r".{10,}", "at least 10 characters"),
    (r"[A-Z]", "one uppercase letter"),
    (r"[a-z]", "one lowercase letter"),
    (r"\d", "one digit"),
    (r"[^A-Za-z0-9]", "one special character"),
)


def require_password(value: Any) -> str:
    """Strong password policy for change/reset (not applied to login of existing users)."""
    password = "" if value is None else str(value)
    if not password:
        raise ValidationError("Password cannot be empty.")
    if password.strip() != password:
        raise ValidationError("Password cannot start or end with spaces.")
    missing = [label for pattern, label in _PASSWORD_RULES if not re.search(pattern, password)]
    if missing:
        raise ValidationError(
            "Password must include: " + ", ".join(missing) + "."
        )
    if len(password) > 128:
        raise ValidationError("Password must be at most 128 characters.")
    return password


def require_role_code(value: Any) -> str:
    code = require_nonempty(value, "Role code").lower()
    if " " in code:
        raise ValidationError("Role code cannot contain spaces.")
    return code


def require_category_name(value: Any) -> str:
    name = require_nonempty(value, "Category name")
    if len(name) > 128:
        raise ValidationError("Category name must be at most 128 characters.")
    return name


def require_score(value: Any, label: str) -> float:
    try:
        score = float(value if value is not None else 0)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} must be a number.") from exc
    if score < 0 or score > 1_000:
        raise ValidationError(f"{label} must be between 0 and 1000.")
    return score


def require_read_time(value: Any) -> Optional[int]:
    if value is None or str(value).strip() == "":
        return None
    try:
        minutes = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Estimated read time must be a whole number.") from exc
    if minutes < 1 or minutes > 240:
        raise ValidationError("Estimated read time must be between 1 and 240 minutes.")
    return minutes


def validate_content_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    title = record.get("title", "")
    body = record.get("content_body") or record.get("text") or ""
    category = str(record.get("category") or record.get("category_name") or "").lower()
    headline_ok = category in {"headline", "headlines", "sarcasm"} or (
        str(title).strip() == str(body).strip() and len(str(title).strip()) >= MIN_TITLE_LENGTH
    )
    if not is_valid_title(title):
        errors.append("title_too_short")
    if not is_valid_body(body, headline_ok=headline_ok):
        errors.append("body_too_short")
    status = (record.get("status") or "draft").lower()
    if not is_allowed_content_status(status):
        errors.append("invalid_status")
    return errors
