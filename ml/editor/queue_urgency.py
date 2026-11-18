"""Editor queue urgency model.

Tells the editor how urgent a story is for the review queue:
  urgent > high > medium > low

This is NOT the same as AIA "pitch importance" (that one is a simple formula).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix, hstack

from utils.logger import get_logger

log = get_logger("ml.editor.queue_urgency")

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATHS = (
    ROOT / "artifacts" / "models" / "editor_queue_urgency.joblib",
)

# Model training labels → simple desk levels used in the app
LABEL_TO_URGENCY = {
    "very low": "low",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "very high": "urgent",
}


@lru_cache(maxsize=1)
def _load_model() -> dict[str, Any] | None:
    path = next((p for p in MODEL_PATHS if p.exists()), None)
    if path is None:
        log.warning("editor_queue_urgency.joblib not found")
        return None
    try:
        import joblib

        bundle = joblib.load(path)
        if not {"model", "tfidf", "labels", "urg_regex"}.issubset(bundle):
            log.warning("Urgency model file is missing required keys: %s", path)
            return None
        log.info("Loaded editor queue urgency model from %s", path)
        return bundle
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not load urgency model: %s", exc)
        return None


def model_available() -> bool:
    return _load_model() is not None


def clear_cache() -> None:
    _load_model.cache_clear()


def _extra_features(texts: list[str], urg_regex: str) -> np.ndarray:
    """Simple extra signals: length, urgent words, digits, ALLCAPS runs."""
    rows = []
    urg = re.compile(urg_regex, re.I)
    digit = re.compile(r"\d")
    caps = re.compile(r"[A-Z]{4,}")
    for text in texts:
        raw = text or ""
        rows.append(
            [
                len(raw) / 500.0,
                len(urg.findall(raw)),
                1 if digit.search(raw) else 0,
                len(caps.findall(raw)),
            ]
        )
    return np.asarray(rows, dtype=float)


def predict_editor_queue_urgency(headline: str, body: str = "") -> dict[str, Any]:
    """Return how urgent this story is for the editor queue."""
    bundle = _load_model()
    text = f"{headline or ''}. {body or ''}".strip()

    if bundle is None:
        return {
            "urgency": "medium",
            "model_label": None,
            "confidence": None,
            "probabilities": {},
            "source": "fallback",
        }

    labels: list[str] = list(bundle["labels"])
    features = hstack(
        [
            bundle["tfidf"].transform([text]),
            csr_matrix(_extra_features([text], str(bundle["urg_regex"]))),
        ]
    ).tocsr()

    probs = bundle["model"].predict_proba(features)[0]
    best = int(np.argmax(probs))
    model_label = labels[best]

    return {
        "urgency": LABEL_TO_URGENCY.get(model_label, "medium"),
        "model_label": model_label,
        "confidence": round(float(probs[best]), 4),
        "probabilities": {label: round(float(p), 4) for label, p in zip(labels, probs)},
        "source": "model",
    }
