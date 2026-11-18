"""Ensure this project's packages win over the parent NewsMind AI tree."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent.resolve()

cleaned: list[str] = []
for entry in sys.path:
    try:
        resolved = Path(entry).resolve()
    except OSError:
        cleaned.append(entry)
        continue
    if resolved == PARENT:
        continue
    cleaned.append(entry)
sys.path[:] = cleaned
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="module")
def db_ready():
    """Integration tests need a live Postgres schema; skip if unavailable."""
    from database.connection import check_connection, init_schema

    if not check_connection():
        pytest.skip("PostgreSQL not available")
    try:
        init_schema()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"init_schema failed: {exc}")
    return True
