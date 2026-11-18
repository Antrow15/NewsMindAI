"""CSV ingestion — full files, single file, or new/changed files only."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

from config.runtime import csv_chunk_rows, max_csv_mb_warn
from dao.ingest_file_dao import IngestFileDAO
from utils.csv_fields import normalize_row
from utils.errors import NotFoundError, ValidationError
from utils.helpers import project_path
from utils.logger import get_logger

log = get_logger("ingestion")


def summarize_records(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_category: dict[str, int] = {}
    titles: set[str] = set()
    for row in rows:
        cat = str(row.get("category") or "Unknown")
        by_category[cat] = by_category.get(cat, 0) + 1
        title = str(row.get("title") or "").strip().lower()
        if title:
            titles.add(title)
    return {
        "list_count": len(rows),
        "categories": sorted(by_category.keys()),
        "unique_titles": len(titles),
        "by_category_counts": by_category,
    }


# Backward-compatible name used by older tests
memory_collection_demo = summarize_records


class IngestionService:
    def __init__(self, raw_dir: Path | None = None) -> None:
        self.raw_dir = raw_dir or project_path("data", "raw")
        self.files = IngestFileDAO()

    def list_csv_files(self) -> list[str]:
        if not self.raw_dir.exists():
            return []
        out: list[str] = []
        for path in sorted(self.raw_dir.rglob("*.csv")):
            if not path.is_file():
                continue
            try:
                out.append(path.relative_to(self.raw_dir).as_posix())
            except ValueError:
                out.append(path.name)
        return out

    def resolve_csv(self, source_file: str) -> Path:
        rel = (source_file or "").strip().replace("\\", "/")
        if not rel:
            raise ValidationError("CSV file path cannot be empty.")
        if rel.lower().endswith(".csv") is False:
            raise ValidationError("Only CSV files are supported.")
        path = (self.raw_dir / rel).resolve()
        raw_root = self.raw_dir.resolve()
        if raw_root not in path.parents and path != raw_root:
            # allow exact file under raw_dir
            try:
                path.relative_to(raw_root)
            except ValueError as exc:
                raise ValidationError("CSV path must be inside data/raw.") from exc
        if not path.exists() or not path.is_file():
            raise NotFoundError(f"CSV file not found: {rel}")
        return path

    def _file_hash(self, path: Path) -> str:
        digest = hashlib.md5()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.raw_dir).as_posix()
        except ValueError:
            return path.name

    def _read_csv(self, path: Path) -> tuple[list[dict[str, Any]], int, int]:
        """Return usable rows, total raw rows, usable count (chunked CSV read)."""
        from utils.progress import progress

        rel = self._rel(path)
        size_mb = path.stat().st_size / (1024 * 1024)
        warn_mb = max_csv_mb_warn()
        if size_mb >= warn_mb:
            progress(
                f"Large CSV detected: {rel} ({size_mb:.1f} MB). Reading in chunks..."
            )
            log.warning(
                "Large CSV: file=%s size_mb=%.1f warn_at=%s",
                rel,
                size_mb,
                warn_mb,
            )
        chunk_size = csv_chunk_rows()
        progress(f"Reading CSV in chunks of {chunk_size}: {rel}")
        usable: list[dict[str, Any]] = []
        total = 0
        chunk_index = 0
        try:
            reader = pd.read_csv(path, chunksize=chunk_size, low_memory=True)
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"Failed to read CSV '{rel}': {exc}") from exc
        try:
            for chunk in reader:
                chunk_index += 1
                if chunk.empty:
                    continue
                chunk.columns = [str(c).strip().lower() for c in chunk.columns]
                rows = [normalize_row(row, source_file=rel) for row in chunk.to_dict(orient="records")]
                total += len(rows)
                usable.extend(r for r in rows if r.get("title"))
                if chunk_index == 1 or chunk_index % 5 == 0:
                    progress(
                        f"  chunk {chunk_index}: rows so far={total}, usable={len(usable)}"
                    )
                del rows
                del chunk
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"Failed while chunk-reading CSV '{rel}': {exc}") from exc
        progress(f"Finished reading {rel}: total={total}, usable={len(usable)}")
        return usable, total, len(usable)

    def file_needs_ingest(self, source_file: str) -> bool:
        path = self.resolve_csv(source_file)
        rel = self._rel(path)
        current = self.files.get_by_source(rel)
        if current is None:
            return True
        return current.get("file_hash") != self._file_hash(path)

    def list_new_or_changed_files(self) -> list[str]:
        return [rel for rel in self.list_csv_files() if self.file_needs_ingest(rel)]

    def load_one_csv(self, source_file: str, *, register: bool = True) -> dict[str, Any]:
        path = self.resolve_csv(source_file)
        rel = self._rel(path)
        rows, total, usable = self._read_csv(path)
        file_hash = self._file_hash(path)
        if register:
            self.files.upsert(
                source_file=rel,
                file_hash=file_hash,
                row_count=total,
                usable_row_count=usable,
                last_status="ingested",
            )
        log.info("Ingested file=%s total=%s usable=%s", rel, total, usable)
        return {
            "records": rows,
            "collections": summarize_records(rows),
            "source_files": [rel],
            "file_hash": file_hash,
            "row_count": total,
            "usable_row_count": usable,
        }

    def load_csv_files(self, source_files: list[str] | None = None, *, register: bool = True) -> list[dict[str, Any]]:
        from utils.progress import progress

        targets = source_files if source_files is not None else self.list_csv_files()
        rows: list[dict[str, Any]] = []
        total = len(targets)
        for index, rel in enumerate(targets, start=1):
            progress(f"Loading file {index}/{total}: {rel}")
            payload = self.load_one_csv(rel, register=register)
            rows.extend(payload["records"])
        return rows

    def ingest_all_content(self, *, only_new: bool = False) -> dict[str, Any]:
        from utils.progress import progress

        files = self.list_new_or_changed_files() if only_new else self.list_csv_files()
        if only_new and not files:
            progress("No new or changed CSV files to ingest.")
            return {
                "records": [],
                "collections": summarize_records([]),
                "source_files": [],
                "message": "No new or changed CSV files to ingest.",
            }
        progress(f"Ingesting {len(files)} CSV file(s)...")
        combined = self.load_csv_files(files, register=True)
        summary = summarize_records(combined)
        progress(f"Ingest complete: files={len(files)} rows={summary['list_count']}")
        log.info("Ingest complete files=%s rows=%s", len(files), summary["list_count"])
        return {
            "records": combined,
            "collections": summary,
            "source_files": files,
        }

    def ingest_one(self, source_file: str) -> dict[str, Any]:
        return self.load_one_csv(source_file, register=True)

    def ingest_pitches(self) -> list[dict[str, Any]]:
        path = self.raw_dir / "pitches.csv"
        if not path.exists():
            return []
        rows, _, _ = self._read_csv(path)
        for row in rows:
            row.setdefault("status", "submitted")
            row["source_type"] = "csv:pitches.csv"
        return rows

    def registered_files(self) -> list[dict[str, Any]]:
        return self.files.list_all()
