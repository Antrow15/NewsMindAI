"""3 — Metadata Extraction."""

from __future__ import annotations

from typing import Any

from ml.common import extract_entities


def extract_metadata(text: str) -> dict[str, Any]:
    """Extract people, orgs, locations, dates from text."""
    entities = extract_entities(text)
    return {
        "people": entities.get("people") or [],
        "organizations": entities.get("organizations") or [],
        "locations": entities.get("locations") or [],
        "dates": entities.get("dates") or [],
        "other": entities.get("other") or [],
    }
