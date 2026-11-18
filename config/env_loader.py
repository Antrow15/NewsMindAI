"""Load key=value pairs from project .env into os.environ (no extra dependency)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_LOADED = False


def load_dotenv(path: Path | None = None) -> Path | None:
    global _LOADED
    if _LOADED:
        return path
    env_path = path or (ROOT / ".env")
    if not env_path.exists():
        _LOADED = True
        return None
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    _LOADED = True
    return env_path
