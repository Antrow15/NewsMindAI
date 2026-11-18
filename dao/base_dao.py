"""Shared DAO helpers."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from database.connection import db_cursor


class BaseDAO:
    table: str = ""

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None, fetch: str = "none") -> Any:
        with db_cursor() as cur:
            cur.execute(sql, params)
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            return cur.rowcount

    def get_by_id(self, pk_name: str, pk_value: int) -> Optional[dict[str, Any]]:
        row = self.execute(
            f"SELECT * FROM {self.table} WHERE {pk_name} = %s",
            (pk_value,),
            fetch="one",
        )
        return dict(row) if row else None

    def delete_by_id(self, pk_name: str, pk_value: int) -> int:
        return int(
            self.execute(
                f"DELETE FROM {self.table} WHERE {pk_name} = %s",
                (pk_value,),
            )
        )

    def list_all(self, limit: int = 500) -> list[dict[str, Any]]:
        rows = self.execute(f"SELECT * FROM {self.table} ORDER BY 1 DESC LIMIT %s", (limit,), fetch="all")
        return [dict(r) for r in rows or []]
