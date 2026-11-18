"""Stakeholder desk: Content Adaptation Editor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ContentAdaptationEditor:
    cae_id: Optional[int] = None
    user_id: Optional[int] = None
    specialization_channel: Optional[str] = None
    status: str = "active"
