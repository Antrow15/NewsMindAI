"""Content validation + knowledge-base relevancy for journalist drafts."""

from __future__ import annotations

from typing import Any, Mapping

from ml.knowledge import score_content_relevancy
from utils.validators import validate_content_record


def validate_article(record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Check required fields and score relevancy against the knowledge base."""
    row = dict(record or {})
    errors = validate_content_record(row)
    title = str(row.get("title") or "")
    body = str(
        row.get("content_body")
        or row.get("body")
        or row.get("summary")
        or row.get("text")
        or ""
    )
    relevancy = score_content_relevancy(title, body)
    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "title": title,
        "relevancy": relevancy.get("relevancy"),
        "relevancy_score": relevancy.get("best_score"),
        "relevancy_matches": relevancy.get("matches", [])[:5],
        "knowledge_base_size": relevancy.get("knowledge_base_size"),
        "source": "knowledge_base",
    }
