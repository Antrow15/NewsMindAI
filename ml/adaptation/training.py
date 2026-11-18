"""Train one unified CAE sentence-retention model for all platforms."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline

from config.constants import ADAPTATION_PLATFORMS
from ml.adaptation.features import SentenceFeatureExtractor
from ml.adaptation.labeling import build_sentence_records
from ml.adaptation.model_loader import clear_model_cache

# Default keep threshold; predict can still apply per-platform overrides.
PLATFORM_THRESHOLDS = {
    "SOCIAL_MEDIA": 0.70,
    "EMAIL_NEWSLETTER": 0.55,
    "PRINT_NEWSPAPER": 0.40,
    "WEBSITE": 0.35,
}
DEFAULT_THRESHOLD = 0.50

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "artifacts" / "models"
CAE_FOLDER = "cae"


def grouped_split(sentence_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    first_split = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=42)
    train_indexes, remaining_indexes = next(
        first_split.split(sentence_df, groups=sentence_df["article_id"])
    )
    train_df = sentence_df.iloc[train_indexes].reset_index(drop=True)
    remaining_df = sentence_df.iloc[remaining_indexes].reset_index(drop=True)
    second_split = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=42)
    validation_indexes, test_indexes = next(
        second_split.split(remaining_df, groups=remaining_df["article_id"])
    )
    validation_df = remaining_df.iloc[validation_indexes].reset_index(drop=True)
    test_df = remaining_df.iloc[test_indexes].reset_index(drop=True)
    return train_df, validation_df, test_df


def evaluate(pipeline: Pipeline, frame: pd.DataFrame, threshold: float) -> dict:
    features = frame.to_dict("records")
    actual = frame["label"].to_numpy()
    probabilities = pipeline.predict_proba(features)[:, 1]
    predicted = (probabilities >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        actual, predicted, average="binary", zero_division=0
    )
    ap = (
        float(average_precision_score(actual, probabilities))
        if len(set(actual)) >= 2
        else 0.0
    )
    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "average_precision": ap,
        "confusion_matrix": confusion_matrix(actual, predicted, labels=[0, 1]).tolist(),
        "records": int(len(frame)),
    }


def _print_matrix(label: str, split: str, metrics: dict) -> None:
    cm = metrics["confusion_matrix"]
    print()
    print(f"{label} — {split} metrics")
    print("-" * 70)
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1: {metrics['f1']:.4f}")
    print(f"Average precision: {metrics['average_precision']:.4f}")
    print(f"Records: {metrics['records']}")
    print("Confusion matrix [[TN, FP], [FN, TP]]:")
    print(f"  {cm[0]}")
    print(f"  {cm[1]}")


def validate_source_dataset(dataframe: pd.DataFrame) -> pd.DataFrame:
    required = {
        "article_id",
        "original_title",
        "original_content",
        "target_platform",
        "correct_adapted_article",
    }
    missing = required - set(dataframe.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    cleaned = dataframe.copy()
    for col in required:
        cleaned[col] = cleaned[col].fillna("").astype(str).str.strip()
    empty = cleaned[
        (cleaned["article_id"] == "")
        | (cleaned["original_content"] == "")
        | (cleaned["correct_adapted_article"] == "")
    ]
    if not empty.empty:
        raise ValueError(f"{len(empty)} rows missing required text fields.")
    supported = set(ADAPTATION_PLATFORMS)
    unsupported = set(cleaned["target_platform"].unique()) - supported
    if unsupported:
        raise ValueError(f"Unsupported platforms: {sorted(unsupported)}")
    print()
    print("Source dataset validation")
    print("-" * 70)
    print(f"Dataset rows: {len(cleaned)}")
    print(f"Unique articles: {cleaned['article_id'].nunique()}")
    print(cleaned["target_platform"].value_counts().to_string())
    return cleaned


def train_unified_model(
    source_df: pd.DataFrame,
    output_root: Path,
    version: str = "1.0.0",
) -> dict:
    print()
    print("=" * 70)
    print("Preparing unified CAE model (all platforms)")
    print("=" * 70)

    sentence_rows: list[dict] = []
    for row in source_df.to_dict("records"):
        sentence_rows.extend(build_sentence_records(row))
    sentence_df = pd.DataFrame(sentence_rows)
    if sentence_df.empty:
        raise ValueError("No sentence records generated for CAE training.")

    label_counts = sentence_df["label"].value_counts().sort_index().to_dict()
    article_count = int(sentence_df["article_id"].nunique())
    print(f"Paired articles: {len(source_df)}")
    print(f"Unique articles: {article_count}")
    print(f"Sentence records: {len(sentence_df)}")
    print(f"Label distribution: {label_counts}")
    print(f"Platforms: {sorted(sentence_df['platform'].unique())}")
    if sentence_df["label"].nunique() < 2:
        raise ValueError(f"Need both classes for CAE: {label_counts}")

    train_df, validation_df, test_df = grouped_split(sentence_df)
    for name, frame in (
        ("training", train_df),
        ("validation", validation_df),
        ("testing", test_df),
    ):
        counts = frame["label"].value_counts().sort_index().to_dict()
        print(f"CAE {name} labels: {counts}")
        if frame["label"].nunique() < 2:
            raise ValueError(f"CAE {name} has one class only: {counts}")

    pipeline = Pipeline(
        steps=[
            ("features", SentenceFeatureExtractor()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2500,
                    class_weight="balanced",
                    C=1.0,
                    solver="liblinear",
                    random_state=42,
                ),
            ),
        ]
    )
    print("Training unified CAE model...")
    pipeline.fit(train_df.to_dict("records"), train_df["label"].to_numpy())

    threshold = DEFAULT_THRESHOLD
    metrics = {
        "validation": evaluate(pipeline, validation_df, threshold),
        "test": evaluate(pipeline, test_df, threshold),
    }
    _print_matrix("CAE (all platforms)", "validation", metrics["validation"])
    _print_matrix("CAE (all platforms)", "test", metrics["test"])

    # Per-platform test slices (same model, platform-specific threshold)
    per_platform: dict[str, dict] = {}
    for platform in ADAPTATION_PLATFORMS:
        slice_df = test_df[test_df["platform"] == platform]
        if slice_df.empty or slice_df["label"].nunique() < 2:
            continue
        plat_threshold = PLATFORM_THRESHOLDS.get(platform, threshold)
        plat_metrics = evaluate(pipeline, slice_df, plat_threshold)
        per_platform[platform] = plat_metrics
        _print_matrix(platform, "test", plat_metrics)

    test_probs = pipeline.predict_proba(test_df.to_dict("records"))[:, 1]
    test_pred = (test_probs >= threshold).astype(int)
    print()
    print(classification_report(test_df["label"], test_pred, digits=3, zero_division=0))
    print(
        pd.DataFrame(
            confusion_matrix(test_df["label"], test_pred, labels=[0, 1]),
            index=["actual_0", "actual_1"],
            columns=["pred_0", "pred_1"],
        )
    )

    platform_folder = output_root / CAE_FOLDER
    platform_folder.mkdir(parents=True, exist_ok=True)
    model_path = platform_folder / "model.joblib"
    metadata_path = platform_folder / "metadata.json"
    metrics_path = platform_folder / "metrics.json"
    joblib.dump(pipeline, model_path)

    metadata = {
        "model": "content_adaptation",
        "version": version,
        "algorithm": "LogisticRegression",
        "feature_extractor": "Word TF-IDF + Character TF-IDF + Manual Features + Platform",
        "threshold": threshold,
        "platform_thresholds": PLATFORM_THRESHOLDS,
        "platforms": list(ADAPTATION_PLATFORMS),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "paired_records": int(len(source_df)),
        "unique_articles": article_count,
        "sentence_records": int(len(sentence_df)),
        "train_records": int(len(train_df)),
        "validation_records": int(len(validation_df)),
        "test_records": int(len(test_df)),
        "label_distribution": {str(k): int(v) for k, v in label_counts.items()},
    }
    # Sidecar for runtime: default threshold + per-platform overrides + version only extras needed
    sidecar_metadata = {
        "version": version,
        "threshold": threshold,
        "platform_thresholds": PLATFORM_THRESHOLDS,
    }
    metadata_path.write_text(json.dumps(sidecar_metadata, indent=2), encoding="utf-8")
    metrics_path.write_text(
        json.dumps({"overall": metrics, "per_platform": per_platform}, indent=2),
        encoding="utf-8",
    )
    print(f"Model saved: {model_path}")
    clear_model_cache()
    return {
        "metadata": metadata,
        "metrics": metrics,
        "per_platform": per_platform,
    }


def train_all_from_dataframe(
    source_df: pd.DataFrame,
    output_root: Path | None = None,
    version: str = "1.0.0",
) -> dict:
    """Train the single shared CAE model. Name kept for console compatibility."""
    source_df = validate_source_dataset(source_df)
    output_directory = Path(output_root or DEFAULT_OUTPUT)
    output_directory.mkdir(parents=True, exist_ok=True)
    result = train_unified_model(
        source_df=source_df,
        output_root=output_directory,
        version=version,
    )
    summary_path = output_directory / "training_summary.json"
    summary = {"content_adaptation": result}
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print()
    print("=" * 70)
    print("Unified CAE model trained successfully")
    print(f"Training summary: {summary_path}")
    print("=" * 70)
    return summary
