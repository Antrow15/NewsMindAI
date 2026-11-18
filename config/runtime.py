"""Runtime settings loaded from environment (.env).

Controls CSV reading batches, DB insert batches, processed-file snapshots,
multi-file pipeline strategy, and hosted Postgres connect options.
"""

from __future__ import annotations

import os

from config.env_loader import load_dotenv


def _int(name: str, default: int) -> int:
    load_dotenv()
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    load_dotenv()
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def csv_chunk_rows() -> int:
    """Pandas chunk size when reading CSV files."""
    return max(500, _int("NEWSROOM_CSV_CHUNK_ROWS", 2000))


def db_insert_batch() -> int:
    """Rows per batch when bulk-inserting raw ingest rows."""
    return max(50, _int("NEWSROOM_DB_INSERT_BATCH", 200))


def max_csv_mb_warn() -> int:
    """Warn in logs/console when a single CSV is larger than this (MB)."""
    return max(1, _int("NEWSROOM_MAX_CSV_MB_WARN", 15))


def write_processed_files() -> bool:
    """Write optional snapshots under data/processed (DB reports remain source of truth)."""
    return _bool("NEWSROOM_WRITE_PROCESSED_FILES", False)


def pipeline_file_by_file() -> bool:
    """When true, multi-file pipelines run one CSV at a time (ingest→clean→persist)."""
    return _bool("NEWSROOM_PIPELINE_FILE_BY_FILE", True)


def db_connect_timeout() -> int:
    return max(3, _int("NEWSROOM_DB_CONNECT_TIMEOUT", 10))


def db_sslmode() -> str:
    load_dotenv()
    return os.environ.get("NEWSROOM_DB_SSLMODE", "prefer").strip() or "prefer"
