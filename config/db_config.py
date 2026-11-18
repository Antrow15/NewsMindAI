"""Database configuration for the NewsMind console backend (local or hosted)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from config.env_loader import load_dotenv
from config.runtime import db_connect_timeout, db_sslmode


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str
    connect_timeout: int = 10
    sslmode: str = "prefer"

    def dsn_kwargs(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.name,
            "user": self.user,
            "password": self.password,
            "connect_timeout": self.connect_timeout,
            "sslmode": self.sslmode,
            # TCP keepalives for hosted / remote Postgres connections
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 3,
        }


def load_db_config() -> DatabaseConfig:
    load_dotenv()
    return DatabaseConfig(
        host=os.environ.get("NEWSROOM_DB_HOST", "localhost"),
        port=int(os.environ.get("NEWSROOM_DB_PORT", "5432")),
        name=os.environ.get("NEWSROOM_DB_NAME", "newsmind_console"),
        user=os.environ.get("NEWSROOM_DB_USER", "postgres"),
        password=os.environ.get("NEWSROOM_DB_PASSWORD", "admin"),
        connect_timeout=db_connect_timeout(),
        sslmode=db_sslmode(),
    )
