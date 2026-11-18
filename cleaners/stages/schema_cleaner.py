"""Type coercion, enums, date parsing."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from cleaners.stages.base_cleaner import BaseCleaner, CleanerResult
from config.constants import ALLOWED_CONTENT_STATUSES, ALLOWED_PITCH_STATUSES, CONTENT_KINDS
from utils.helpers import coerce_str
from utils.validators import validate_content_record


def _parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = coerce_str(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


class SchemaCleaner(BaseCleaner):
    name = "schema_cleaner"

    def __init__(self, record_type: str = "content") -> None:
        self.record_type = record_type

    def clean(self, records: list[dict[str, Any]]) -> CleanerResult:
        kept: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for row in records:
            out = dict(row)
            out["title"] = coerce_str(out.get("title"))
            body = coerce_str(out.get("text") or out.get("content_body"))
            out["text"] = body
            out["content_body"] = body
            out["category"] = coerce_str(out.get("category") or out.get("category_name") or "City")
            out["category_name"] = out["category"]
            kind = coerce_str(out.get("content_kind") or out.get("kind") or "article").lower()
            out["content_kind"] = kind if kind in CONTENT_KINDS else "article"
            status = coerce_str(out.get("status") or "draft").lower()
            if self.record_type == "pitch":
                out["status"] = status if status in ALLOWED_PITCH_STATUSES else "submitted"
            else:
                out["status"] = status if status in ALLOWED_CONTENT_STATUSES else "draft"
            out["published_date"] = _parse_date(out.get("date") or out.get("published_date"))
            for score_key in ("trend_score", "audience_interest_score", "coverage_gap_score"):
                try:
                    out[score_key] = float(out.get(score_key) or 0.0)
                except (TypeError, ValueError):
                    out[score_key] = 0.0

            if self.record_type != "pitch":
                errors = validate_content_record(out)
                if errors:
                    rejected.append({**out, "_reject_reason": ",".join(errors)})
                    continue
            kept.append(out)
        return CleanerResult(
            kept=kept,
            rejected=rejected,
            stats={"input": len(records), "kept": len(kept), "rejected": len(rejected)},
        )
