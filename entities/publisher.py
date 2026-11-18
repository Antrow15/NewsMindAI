"""Stakeholder desk: Publisher."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Publisher:
    publisher_id: Optional[int] = None
    user_id: Optional[int] = None
    publishing_group: Optional[str] = None
    status: str = "active"
