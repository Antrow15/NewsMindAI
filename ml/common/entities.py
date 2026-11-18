"""Named-entity helpers.

Uses spaCy as a supporting library with a **blank** English pipeline + EntityRuler
(no trained model download, no model training). Falls back to regex if spaCy
is not installed.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

_PERSON = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
_DATE = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}|"
    r"\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
_ORG = re.compile(
    r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+"
    r"(?:Inc|Corp|Company|Ltd|LLC|University|Ministry|Commission|Agency))\b"
)
_LOCATION = re.compile(
    r"\b(?:in|at|from|near)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
)

_EMPTY: dict[str, list[str]] = {
    "people": [],
    "organizations": [],
    "locations": [],
    "dates": [],
    "other": [],
}


def _regex_entities(text: str) -> dict[str, list[str]]:
    return {
        "people": list(dict.fromkeys(_PERSON.findall(text))),
        "organizations": list(dict.fromkeys(_ORG.findall(text))),
        "locations": list(dict.fromkeys(_LOCATION.findall(text))),
        "dates": list(dict.fromkeys(_DATE.findall(text))),
        "other": [],
    }


@lru_cache(maxsize=1)
def _spacy_ruler():
    """Blank spaCy English + pattern ruler. Never downloads a model."""
    import spacy
    from spacy.pipeline import EntityRuler

    nlp = spacy.blank("en")
    ruler: EntityRuler = nlp.add_pipe("entity_ruler")
    patterns: list[dict[str, Any]] = [
        {"label": "DATE", "pattern": [{"SHAPE": "dd/dd/dddd"}]},
        {"label": "DATE", "pattern": [{"SHAPE": "dddd-dd-dd"}]},
        {
            "label": "ORG",
            "pattern": [
                {"IS_TITLE": True, "OP": "+"},
                {"LOWER": {"IN": ["inc", "corp", "company", "ltd", "llc", "university", "ministry", "commission", "agency"]}},
            ],
        },
        {
            "label": "PERSON",
            "pattern": [{"IS_TITLE": True}, {"IS_TITLE": True}],
        },
        {
            "label": "GPE",
            "pattern": [
                {"LOWER": {"IN": ["in", "at", "from", "near"]}},
                {"IS_TITLE": True},
            ],
        },
    ]
    ruler.add_patterns(patterns)
    return nlp


def _spacy_entities(text: str) -> dict[str, list[str]] | None:
    try:
        nlp = _spacy_ruler()
    except Exception:  # noqa: BLE001 — spaCy missing or pipe setup failed
        return None

    doc = nlp(text)
    result: dict[str, list[str]] = {
        "people": [],
        "organizations": [],
        "locations": [],
        "dates": [],
        "other": [],
    }
    seen: set[tuple[str, str]] = set()
    for ent in doc.ents:
        value = ent.text.strip()
        # EntityRuler GPE pattern includes the preposition — keep the place name only
        if ent.label_ == "GPE" and " " in value:
            value = value.split(None, 1)[-1]
        key = (ent.label_, value.lower())
        if not value or key in seen:
            continue
        seen.add(key)
        if ent.label_ == "PERSON":
            result["people"].append(value)
        elif ent.label_ == "ORG":
            result["organizations"].append(value)
        elif ent.label_ in {"GPE", "LOC"}:
            result["locations"].append(value)
        elif ent.label_ == "DATE":
            result["dates"].append(value)
        else:
            result["other"].append(value)

    # Merge regex hits so month-name dates and similar still appear
    regex = _regex_entities(text)
    for field in ("people", "organizations", "locations", "dates"):
        merged = list(dict.fromkeys([*result[field], *regex[field]]))
        result[field] = merged
    return result


def extract_entities(text: str) -> dict[str, list[str]]:
    """Extract people, orgs, locations, dates. Empty text → empty lists."""
    raw = "" if text is None else str(text).strip()
    if not raw:
        return dict(_EMPTY)

    spacy_result = _spacy_entities(raw)
    if spacy_result is not None:
        return spacy_result
    return _regex_entities(raw)
