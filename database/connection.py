"""PostgreSQL connectivity for the NewsMind console backend."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

from config.db_config import DatabaseConfig, load_db_config
from utils.logger import get_logger

log = get_logger("db")
ROOT = Path(__file__).resolve().parents[1]


def get_connection(cfg: Optional[DatabaseConfig] = None) -> PgConnection:
    cfg = cfg or load_db_config()
    return psycopg2.connect(**cfg.dsn_kwargs())


@contextmanager
def db_cursor(cfg: Optional[DatabaseConfig] = None) -> Generator:
    cfg = cfg or load_db_config()
    conn = get_connection(cfg)
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()


def apply_sql_file(path: Path, cfg: Optional[DatabaseConfig] = None) -> None:
    """Apply a SQL file statement-by-statement so later upgrades still run after IF NOT EXISTS creates."""
    raw = path.read_text(encoding="utf-8")
    # Strip line comments, then split on semicolons
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    text = "\n".join(lines)
    statements = [s.strip() for s in text.split(";") if s.strip()]
    cfg = cfg or load_db_config()
    conn = get_connection(cfg)
    try:
        with conn:
            with conn.cursor() as cur:
                for stmt in statements:
                    cur.execute(stmt)
        log.info("Applied SQL file %s (%s statements)", path.name, len(statements))
    finally:
        conn.close()


def init_schema(cfg: Optional[DatabaseConfig] = None) -> None:
    cfg = cfg or load_db_config()
    apply_sql_file(ROOT / "database" / "schema.sql", cfg)
    apply_sql_file(ROOT / "database" / "seed_data.sql", cfg)
    apply_sql_file(ROOT / "database" / "schema_cae_publisher.sql", cfg)
    apply_sql_file(ROOT / "database" / "schema_ml_training.sql", cfg)
    # Existing DBs may still allow orphan evidence rows
    with db_cursor(cfg) as cur:
        cur.execute("DELETE FROM evidence WHERE content_id IS NULL")
        cur.execute(
            """
            DO $$
            BEGIN
                ALTER TABLE evidence ALTER COLUMN content_id SET NOT NULL;
            EXCEPTION WHEN others THEN
                NULL;
            END $$;
            """
        )
    from database.seed_demo_users import seed_demo_users

    seed_demo_users()


def ensure_cae_publisher_schema(cfg: Optional[DatabaseConfig] = None) -> None:
    """Apply CAE/publisher tables without wiping the main schema."""
    apply_sql_file(ROOT / "database" / "schema_cae_publisher.sql", cfg or load_db_config())


def ensure_ml_training_schema(cfg: Optional[DatabaseConfig] = None) -> None:
    """Apply ML training + knowledge_base tables without wiping the main schema."""
    apply_sql_file(ROOT / "database" / "schema_ml_training.sql", cfg or load_db_config())


def check_connection(cfg: Optional[DatabaseConfig] = None) -> bool:
    try:
        with db_cursor(cfg) as cur:
            cur.execute("SELECT 1 AS ok")
            row = cur.fetchone()
            return bool(row and row.get("ok") == 1)
    except Exception as exc:  # noqa: BLE001
        log.error("Database connection failed: %s", exc)
        return False
