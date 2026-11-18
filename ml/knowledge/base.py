"""Knowledge base for journalist content relevancy / related history only.

Seeded only from ``data/news`` + ``data/historical`` (not training or evidence).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ml.common import rank
from utils.logger import get_logger

log = get_logger("ml.knowledge")
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATHS = (
    ROOT / "data" / "news" / "current_news.csv",
    ROOT / "data" / "historical" / "historical_headlines.csv",
)


def _docs_from_csv(paths: tuple[Path, ...] = DEFAULT_CSV_PATHS, limit: int = 4000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        df = pd.read_csv(path)
        title_col = "title" if "title" in df.columns else df.columns[0]
        body_col = "text" if "text" in df.columns else ("body" if "body" in df.columns else title_col)
        cat_col = "category" if "category" in df.columns else None
        for i, row in df.head(limit).iterrows():
            title = str(row.get(title_col) or "").strip()
            body = str(row.get(body_col) or "").strip()
            if not title and not body:
                continue
            rows.append(
                {
                    "id": f"{path.stem}-{i}",
                    "title": title or body[:80],
                    "text": body or title,
                    "category": str(row.get(cat_col) or "") if cat_col else "",
                    "source_tag": path.stem,
                }
            )
    return rows


def ensure_knowledge_base_loaded(*, force: bool = False) -> int:
    """Push CSV knowledge into DB if the table is empty (or force reload)."""
    from database.connection import db_cursor, require_schema

    require_schema()
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM knowledge_base")
        count = int((cur.fetchone() or {}).get("n") or 0)
        if count > 0 and not force:
            return count
        if force:
            cur.execute("TRUNCATE knowledge_base RESTART IDENTITY")
        docs = _docs_from_csv()
        for doc in docs:
            cur.execute(
                """
                INSERT INTO knowledge_base (title, body, category, source_tag)
                VALUES (%s, %s, %s, %s)
                """,
                (doc["title"], doc["text"], doc.get("category") or None, doc.get("source_tag")),
            )
        log.info("Loaded %s knowledge_base rows from CSV", len(docs))
        return len(docs)


def load_knowledge_documents(*, limit: int = 2000) -> list[dict[str, Any]]:
    """Load KB docs from DB; fall back to CSV files if DB unavailable/empty."""
    try:
        from database.connection import db_cursor, require_schema

        require_schema()
        ensure_knowledge_base_loaded()
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT kb_id AS id, title, body AS text, category, source_tag
                FROM knowledge_base
                ORDER BY kb_id
                LIMIT %s
                """,
                (limit,),
            )
            rows = [dict(r) for r in (cur.fetchall() or [])]
            if rows:
                return rows
    except Exception as exc:  # noqa: BLE001
        log.warning("knowledge_base DB load failed, using CSV: %s", exc)
    return _docs_from_csv(limit=limit)


def score_content_relevancy(
    title: str,
    body: str = "",
    *,
    limit: int = 8,
    min_score: float = 0.08,
) -> dict[str, Any]:
    """Rank draft content against the newsroom knowledge base."""
    query = f"{title or ''}. {body or ''}".strip()
    docs = load_knowledge_documents()
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
    return {
        "relevancy": label,
        "best_score": round(best, 4),
        "matches": hits,
        "knowledge_base_size": len(docs),
        "source": "knowledge_base",
    }
