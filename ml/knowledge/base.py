"""Journalist relevancy: TF-IDF + cosine over desk-published ``content`` only.

Corpus = rows in ``content`` with ``status = 'published'`` that were created by
the newsroom desk (not CSV history seeds). No history CSV push.
"""

from __future__ import annotations

from typing import Any

from ml.common import rank
from utils.logger import get_logger

log = get_logger("ml.knowledge")
SEED_PREFIX = "seed/"


def _drop_legacy_knowledge_base() -> None:
    from database.connection import db_cursor

    with db_cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS knowledge_base CASCADE")
        # Clear old history-seed rows if any remain
        cur.execute("DELETE FROM content WHERE source_type LIKE %s", (f"{SEED_PREFIX}%",))


def cleanup_legacy_relevancy_sources() -> None:
    """One-shot cleanup: drop knowledge_base table + seed CSV rows."""
    _drop_legacy_knowledge_base()


def load_published_documents(*, limit: int = 2000) -> list[dict[str, Any]]:
    """Desk-published content only (excludes source_type seed/…)."""
    try:
        from database.connection import db_cursor, require_schema

        _drop_legacy_knowledge_base()
        require_schema()
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    content_id AS id,
                    title,
                    COALESCE(content_body, raw_body, summary, '') AS text,
                    source_type AS category
                FROM content
                WHERE status = 'published'
                  AND (source_type IS NULL OR source_type NOT LIKE %s)
                ORDER BY content_id DESC
                LIMIT %s
                """,
                (f"{SEED_PREFIX}%", limit),
            )
            return [dict(r) for r in (cur.fetchall() or [])]
    except Exception as exc:  # noqa: BLE001
        log.warning("published content load failed: %s", exc)
        return []


def score_content_relevancy(
    title: str,
    body: str = "",
    *,
    limit: int = 8,
    min_score: float = 0.08,
) -> dict[str, Any]:
    """TF-IDF + cosine against desk-published content only."""
    query = f"{title or ''}. {body or ''}".strip()
    docs = load_published_documents()
    hits = [h for h in rank(query, docs, limit=limit) if float(h.get("score") or 0) >= min_score]
    best = float(hits[0]["score"]) if hits else 0.0
    if best >= 0.35:
        label = "high"
    elif best >= 0.15:
        label = "medium"
    elif best > 0:
        label = "low"
    else:
        label = "none"
    size = len(docs)
    return {
        "relevancy": label,
        "best_score": round(best, 4),
        "matches": hits,
        "method": "tfidf_cosine",
        "corpus_size": size,
        "knowledge_base_size": size,
        "source": "content",
    }
