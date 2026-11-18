"""Ingest + clean ML training CSVs before writing ``ml_train_*`` staging tables."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from cleaners.orchestrator import CleaningOrchestrator
from utils.errors import NotFoundError, ValidationError

ROOT = Path(__file__).resolve().parents[2]
URGENCY_DIR = ROOT / "ml" / "editor" / "dataset"
ADAPTATION_DIR = ROOT / "ml" / "adaptation" / "dataset"
DatasetKind = Literal["urgency", "adaptation"]


def list_dataset_csvs(kind: DatasetKind) -> list[str]:
    root = URGENCY_DIR if kind == "urgency" else ADAPTATION_DIR
    if not root.exists():
        return []
    return sorted(p.name for p in root.glob("*.csv") if p.is_file())


def resolve_dataset_csv(kind: DatasetKind, source_file: str | Path | None = None) -> Path:
    root = URGENCY_DIR if kind == "urgency" else ADAPTATION_DIR
    if source_file is None or str(source_file).strip() == "":
        defaults = {
            "urgency": root / "synthetic_news.csv",
            "adaptation": root / "newsmind_paired_examples.csv",
        }
        path = defaults[kind]
    else:
        name = Path(str(source_file)).name
        path = (root / name).resolve()
        if root.resolve() not in path.parents and path != root.resolve():
            raise ValidationError(f"CSV must be inside {root.as_posix()}")
    if not path.exists() or not path.is_file():
        raise NotFoundError(f"Training CSV not found: {path.name} (expected under {root})")
    return path


def file_hash(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _already_pushed(cur, rel: str, digest: str) -> bool:
    cur.execute(
        "SELECT file_hash FROM ml_train_file WHERE source_file = %s",
        (rel,),
    )
    row = cur.fetchone()
    return bool(row and str(row.get("file_hash") or "") == digest)


def _upsert_file_row(cur, *, rel: str, digest: str, kind: str, row_count: int) -> None:
    cur.execute(
        """
        INSERT INTO ml_train_file (source_file, file_hash, dataset_kind, row_count, loaded_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (source_file) DO UPDATE
        SET file_hash = EXCLUDED.file_hash,
            dataset_kind = EXCLUDED.dataset_kind,
            row_count = EXCLUDED.row_count,
            loaded_at = NOW()
        """,
        (rel, digest, kind, row_count),
    )


def _read_csv_records(path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df.to_dict(orient="records")


def _urgency_to_clean_rows(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(raw):
        headline = str(row.get("headline") or row.get("title") or "").strip()
        body = str(row.get("body") or row.get("text") or "").strip()
        priority = str(row.get("priority") or row.get("label") or "").strip().lower()
        source = str(row.get("source") or row.get("source_dataset") or "").strip()
        if not headline and not body:
            continue
        out.append(
            {
                "title": headline or body[:80],
                "text": body or headline,
                "content_body": body or headline,
                "headline": headline or body[:80],
                "body": body,
                "priority": priority,
                "source": source,
                "status": "draft",
                "content_kind": "news",
                "_row": i,
            }
        )
    return out


def _adaptation_to_clean_rows(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(raw):
        title = str(row.get("original_title") or row.get("title") or "").strip()
        body = str(row.get("original_content") or row.get("text") or row.get("body") or "").strip()
        adapted = str(row.get("correct_adapted_article") or "").strip()
        platform = str(row.get("target_platform") or "").strip()
        article_id = str(row.get("article_id") or f"row-{i}").strip()
        if not title or not body or not adapted or not platform:
            continue
        out.append(
            {
                "title": title,
                "text": body,
                "content_body": body,
                "article_id": article_id,
                "original_title": title,
                "original_content": body,
                "target_platform": platform,
                "correct_adapted_article": adapted,
                "status": "draft",
                "content_kind": "article",
                "_row": i,
            }
        )
    return out


def _clean_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []
    result = CleaningOrchestrator().clean_content(records, write_files=False)
    return list(result.get("kept") or [])


def push_urgency_file(csv_path: Path | str | None = None, *, force: bool = False) -> dict[str, Any]:
    from database.connection import db_cursor, require_schema

    require_schema()
    path = resolve_dataset_csv("urgency", csv_path)
    rel = f"ml/editor/dataset/{path.name}"
    digest = file_hash(path)
    with db_cursor() as cur:
        if not force and _already_pushed(cur, rel, digest):
            cur.execute("SELECT COUNT(*) AS n FROM ml_train_urgency WHERE source_file = %s", (rel,))
            n = int((cur.fetchone() or {}).get("n") or 0)
            print(f"Skip urgency push (unchanged): {rel} ({n} rows)")
            return {"skipped": True, "source_file": rel, "rows": n}

        raw = _read_csv_records(path)
        cleaned = _clean_records(_urgency_to_clean_rows(raw))
        cur.execute("DELETE FROM ml_train_urgency WHERE source_file = %s", (rel,))
        kept = 0
        for row in cleaned:
            priority = str(row.get("priority") or "").strip().lower()
            if priority not in {"very low", "low", "medium", "high", "very high"}:
                continue
            cur.execute(
                """
                INSERT INTO ml_train_urgency (source_file, headline, body, source, priority)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    rel,
                    str(row.get("headline") or row.get("title") or ""),
                    str(row.get("body") or row.get("text") or ""),
                    str(row.get("source") or ""),
                    priority,
                ),
            )
            kept += 1
        _upsert_file_row(cur, rel=rel, digest=digest, kind="urgency", row_count=kept)
    print(f"Pushed {kept} cleaned urgency rows → ml_train_urgency ({rel})")
    return {"skipped": False, "source_file": rel, "rows": kept}


def push_adaptation_file(csv_path: Path | str | None = None, *, force: bool = False) -> dict[str, Any]:
    from database.connection import db_cursor, require_schema

    require_schema()
    path = resolve_dataset_csv("adaptation", csv_path)
    rel = f"ml/adaptation/dataset/{path.name}"
    digest = file_hash(path)
    with db_cursor() as cur:
        if not force and _already_pushed(cur, rel, digest):
            cur.execute(
                "SELECT COUNT(*) AS n FROM ml_train_adaptation WHERE source_file = %s",
                (rel,),
            )
            n = int((cur.fetchone() or {}).get("n") or 0)
            print(f"Skip adaptation push (unchanged): {rel} ({n} rows)")
            return {"skipped": True, "source_file": rel, "rows": n}

        raw = _read_csv_records(path)
        cleaned = _clean_records(_adaptation_to_clean_rows(raw))
        cur.execute("DELETE FROM ml_train_adaptation WHERE source_file = %s", (rel,))
        kept = 0
        for row in cleaned:
            cur.execute(
                """
                INSERT INTO ml_train_adaptation
                    (source_file, article_id, original_title, original_content,
                     target_platform, correct_adapted_article)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_file, article_id, target_platform) DO UPDATE
                SET original_title = EXCLUDED.original_title,
                    original_content = EXCLUDED.original_content,
                    correct_adapted_article = EXCLUDED.correct_adapted_article,
                    loaded_at = NOW()
                """,
                (
                    rel,
                    str(row.get("article_id") or ""),
                    str(row.get("original_title") or row.get("title") or ""),
                    str(row.get("original_content") or row.get("text") or ""),
                    str(row.get("target_platform") or ""),
                    str(row.get("correct_adapted_article") or ""),
                ),
            )
            kept += 1
        _upsert_file_row(cur, rel=rel, digest=digest, kind="adaptation", row_count=kept)
    print(f"Pushed {kept} cleaned adaptation rows → ml_train_adaptation ({rel})")
    return {"skipped": False, "source_file": rel, "rows": kept}


def push_all_new(kind: DatasetKind, *, force: bool = False) -> list[dict[str, Any]]:
    results = []
    for name in list_dataset_csvs(kind):
        if kind == "urgency":
            results.append(push_urgency_file(name, force=force))
        else:
            results.append(push_adaptation_file(name, force=force))
    return results
