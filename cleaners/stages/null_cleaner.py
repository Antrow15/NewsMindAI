"""Drop or reject records missing required fields."""

from __future__ import annotations

from typing import Any

from cleaners.stages.base_cleaner import BaseCleaner, CleanerResult
from utils.helpers import coerce_str


class NullCleaner(BaseCleaner):
    name = "null_cleaner"

    def __init__(self, required_fields: tuple[str, ...] = ("title", "text")) -> None:
        self.required_fields = required_fields

    def clean(self, records: list[dict[str, Any]]) -> CleanerResult:
        kept: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for row in records:
            title = coerce_str(row.get("title") or row.get("headline") or row.get("headline_text"))
            body = coerce_str(
                row.get("text")
                or row.get("content_body")
                or row.get("description")
                or row.get("short_description")
            )
            # Headline-only: allow title to fill body
            if title and not body:
                body = title
                row = {**row, "text": body, "content_body": body}

            if not title:
                rejected.append({**row, "_reject_reason": "missing_title"})
                continue
            if not body:
                rejected.append({**row, "_reject_reason": "missing_body"})
                continue

            out = dict(row)
            out["title"] = title
            out["text"] = body
            out["content_body"] = body
            kept.append(out)
        return CleanerResult(
            kept=kept,
            rejected=rejected,
            stats={"input": len(records), "kept": len(kept), "rejected": len(rejected)},
        )
