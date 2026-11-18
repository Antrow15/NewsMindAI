"""Abstract cleaner interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CleanerResult:
    kept: list[dict[str, Any]]
    rejected: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


class BaseCleaner(ABC):
    name: str = "base"

    @abstractmethod
    def clean(self, records: list[dict[str, Any]]) -> CleanerResult:
        raise NotImplementedError
