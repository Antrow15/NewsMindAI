"""Small helper utilities."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]


def project_path(*parts: str) -> Path:
    return ROOT.joinpath(*parts)


def coerce_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def normalize_key(text: str) -> str:
    text = coerce_str(text).lower()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunked(items: Iterable[Any], size: int) -> list[list[Any]]:
    buf: list[Any] = []
    out: list[list[Any]] = []
    for item in items:
        buf.append(item)
        if len(buf) >= size:
            out.append(buf)
            buf = []
    if buf:
        out.append(buf)
    return out
