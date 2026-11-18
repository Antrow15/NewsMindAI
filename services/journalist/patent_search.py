"""7 — Patent Search & Similarity Analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from ml.common import normalize, rank
from utils.helpers import project_path


def load_patent_docs(folder: Path | None = None) -> list[dict[str, Any]]:
    """Load patents from data/patents CSV and optional .txt/.md files."""
    root = folder or project_path("data", "patents")
    docs: list[dict[str, Any]] = []
    if not root.exists():
        return docs

    csv_path = root / "patent_corpus.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        title_col = "title" if "title" in df.columns else df.columns[0]
        body_col = "text" if "text" in df.columns else ("body" if "body" in df.columns else title_col)
        for i, row in df.iterrows():
            title = str(row.get(title_col) or "").strip()
            text = str(row.get(body_col) or "").strip()
            if not title and not text:
                continue
            docs.append({"id": f"patent-csv-{i}", "title": title or text[:80], "text": text or title})

    for path in sorted(root.glob("**/*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        docs.append({"id": path.stem, "title": path.stem, "text": text})
    return docs


def search_patents(
    query: str,
    documents: Sequence[Mapping[str, Any]] | None = None,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Rank patent texts vs query. Uses data/patents corpus when documents is None."""
    if not normalize(query):
        return []
    docs = list(documents) if documents is not None else load_patent_docs()
    return rank(query, docs, limit=limit)
