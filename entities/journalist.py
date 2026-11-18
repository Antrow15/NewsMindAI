"""Stakeholder desk: Journalist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Journalist:
    journalist_id: Optional[int] = None
    user_id: Optional[int] = None
    primary_specialization: Optional[str] = None
    secondary_specialization: Optional[str] = None
    availability_status: str = "available"
    status: str = "active"
