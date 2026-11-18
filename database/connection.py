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
SCHEMA_SQL = ROOT / "database" / "newsmind.sql"


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
    """Apply a SQL file statement-by-statement."""
    raw = path.read_text(encoding="utf-8")
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


def require_schema(cfg: Optional[DatabaseConfig] = None) -> None:
    """Fail fast if the DB was not initialized with newsmind.sql."""
    required = ("users", "content", "ml_train_file", "adaptation_requests")
    with db_cursor(cfg) as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            """,
            (list(required),),
        )
        found = {str(row["table_name"]) for row in cur.fetchall() or []}
    missing = [name for name in required if name not in found]
    if missing:
        raise RuntimeError(
            "Database schema incomplete (missing: "
            + ", ".join(missing)
            + "). Run: python app.py --init-db"
        )


def init_schema(cfg: Optional[DatabaseConfig] = None) -> None:
    """Fresh install from database/newsmind.sql, then seed demo users."""
    cfg = cfg or load_db_config()
    apply_sql_file(SCHEMA_SQL, cfg)
    from database.seed_demo_users import seed_demo_users

    seed_demo_users()


def check_connection(cfg: Optional[DatabaseConfig] = None) -> bool:
    try:
        with db_cursor(cfg) as cur:
            cur.execute("SELECT 1 AS ok")
            row = cur.fetchone()
            return bool(row and row.get("ok") == 1)
    except Exception as exc:  # noqa: BLE001
        log.error("Database connection failed: %s", exc)
        return False
