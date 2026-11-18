"""Content taxonomy: Category."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    category_id: Optional[int] = None
    category_name: str = ""
    description: Optional[str] = None
    is_active: bool = True
