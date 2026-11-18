"""Normalize any CSV news-like columns into canonical fields.

Works for current samples and unknown future datasets (CSV only).
"""

from __future__ import annotations

from typing import Any

from utils.helpers import coerce_str

TITLE_ALIASES = (
    "title",
    "headline",
    "headline_text",
    "headlines",
    "news_title",
    "article_title",
    "name",
    "heading",
    "primary_heading",
    "story_title",
    "subject_line",
)
TEXT_ALIASES = (
    "text",
    "content",
    "content_body",
    "body",
    "article",
    "article_body",
    "description",
    "short_description",
    "summary",
    "story",
    "full_text",
    "full_article",
    "article_text",
    "news_text",
    "content_text",
)
CATEGORY_ALIASES = (
    "category",
    "category_name",
    "subject",
    "section",
    "topic",
    "topic_label",
    "tags",
    "label",
    "class",
    "genre",
    "channel",
)
DATE_ALIASES = (
    "date",
    "published_date",
    "publish_date",
    "publication_date",
    "datetime",
    "time",
    "created_at",
    "published_at",
)
STATUS_ALIASES = ("status", "state")
KIND_ALIASES = ("content_kind", "kind", "type", "article_type", "news_type")
SOURCE_ALIASES = ("source_dataset", "source", "dataset", "origin")
SUMMARY_ALIASES = ("summary", "excerpt", "teaser", "abstract")
SKIP_KEYS = {"id", "index", "unnamed: 0", "row_id", "uuid"}


def _first(row: dict[str, Any], aliases: tuple[str, ...]) -> str:
    for key in aliases:
        if key in row and coerce_str(row.get(key)):
            return coerce_str(row.get(key))
    return ""


def _longest_text_value(row: dict[str, Any], *, exclude: set[str] | None = None) -> str:
    exclude = exclude or set()
    best = ""
    for key, value in row.items():
        if key in exclude or key in SKIP_KEYS:
            continue
        text = coerce_str(value)
        if len(text) > len(best):
            best = text
    return best


def normalize_row(row: dict[str, Any], *, source_file: str = "") -> dict[str, Any]:
    """Map arbitrary CSV columns → title/text/category/date/..."""
    raw = {
        str(k).strip().lower(): v
        for k, v in row.items()
        if str(k).strip() and not str(k).lower().startswith("unnamed")
    }
    raw.pop("", None)

    title = _first(raw, TITLE_ALIASES)
    text = _first(raw, TEXT_ALIASES)
    category = (_first(raw, CATEGORY_ALIASES) or "General")[:128]
    if category.count(",") >= 2:
        category = category.split(",", 1)[0].strip()[:128] or "General"
    date_val = _first(raw, DATE_ALIASES)[:64]
    status = (_first(raw, STATUS_ALIASES) or "draft").lower()
    kind = (_first(raw, KIND_ALIASES) or "article").lower()
    if kind not in {"article", "news"}:
        kind = "article"
    source = (_first(raw, SOURCE_ALIASES) or source_file)[:128]
    summary = _first(raw, SUMMARY_ALIASES)

    # Unknown dataset fallback: use longest string field as body/title
    if not text:
        text = _longest_text_value(raw, exclude={*(TITLE_ALIASES), *(CATEGORY_ALIASES), *(DATE_ALIASES)})
    if not title and text:
        title = text[:120].strip()
    if title and not text:
        text = title
        if category.lower() in {"", "general", "unknown"}:
            category = "Headline"

    out = dict(raw)
    out.update(
        {
            "title": title,
            "text": text,
            "content_body": text,
            "category": category,
            "category_name": category,
            "date": date_val,
            "status": status if status else "draft",
            "content_kind": kind,
            "summary": summary,
            "source_dataset": source,
            "source_type": f"csv:{source_file}" if source_file else coerce_str(raw.get("source_type")),
            "_raw_title": title,
            "_raw_text": text,
            "_source_file": source_file,
        }
    )
    return out
