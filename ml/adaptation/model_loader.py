"""Load the unified CAE sentence-retention model from artifacts/models/cae/."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "artifacts" / "models" / "cae"


@lru_cache(maxsize=1)
def load_model(_platform: str | None = None) -> tuple[object, dict]:
    """Load the single shared CAE model. Platform is kept for API compatibility."""
    model_path = MODEL_DIR / "model.joblib"
    metadata_path = MODEL_DIR / "metadata.json"
    if not model_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            "No trained CAE model. "
            "Push CSV to DB then train CAE via the Admin console ML TRAINING menu, "
            "ml.training.train_cae_from_db(), or: python scripts/train_models_console.py --cae"
        )
    import joblib

    return joblib.load(model_path), json.loads(metadata_path.read_text(encoding="utf-8"))


def clear_model_cache() -> None:
    load_model.cache_clear()
