"""Console model training: CSV → ingest+clean → ``ml_train_*`` → artifacts.

Newsroom ``content`` is never used for training. ML CSVs live under
``ml/editor/dataset`` and ``ml/adaptation/dataset``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def _ensure_schema() -> None:
    from database.connection import require_schema

    require_schema()


def push_urgency(csv_path: Path | str | None = None, *, force: bool = False) -> int:
    from ml.training.ingest_clean import push_all_new, push_urgency_file

    _ensure_schema()
    if csv_path is None:
        results = push_all_new("urgency", force=force)
        if not results:
            result = push_urgency_file(force=force)
            return int(result.get("rows") or 0)
        return sum(int(r.get("rows") or 0) for r in results)
    return int(push_urgency_file(csv_path, force=force).get("rows") or 0)


def push_adaptation(csv_path: Path | str | None = None, *, force: bool = False) -> int:
    from ml.training.ingest_clean import push_adaptation_file, push_all_new

    _ensure_schema()
    if csv_path is None:
        results = push_all_new("adaptation", force=force)
        if not results:
            result = push_adaptation_file(force=force)
            return int(result.get("rows") or 0)
        return sum(int(r.get("rows") or 0) for r in results)
    return int(push_adaptation_file(csv_path, force=force).get("rows") or 0)


def _load_urgency_from_db() -> pd.DataFrame:
    from database.connection import db_cursor

    with db_cursor() as cur:
        cur.execute("SELECT headline, body, source, priority FROM ml_train_urgency")
        rows = cur.fetchall() or []
    return pd.DataFrame([dict(r) for r in rows])


def _load_adaptation_from_db() -> pd.DataFrame:
    from database.connection import db_cursor

    with db_cursor() as cur:
        cur.execute(
            """
            SELECT article_id, original_title, original_content,
                   target_platform, correct_adapted_article
            FROM ml_train_adaptation
            """
        )
        rows = cur.fetchall() or []
    return pd.DataFrame([dict(r) for r in rows])


def train_urgency_from_db(*, fast: bool = False) -> dict:
    """Train urgency using cleaned rows from DB."""
    import re
    import sys
    import time

    import joblib
    import numpy as np
    from scipy.sparse import csr_matrix, hstack
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
    )
    from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
    from xgboost import XGBClassifier

    from utils.progress import progress

    LABELS = ["very low", "low", "medium", "high", "very high"]
    URG_WORDS = (
        r"urgent|breaking|critical|immediate|emergency|severe|ban|sanction|"
        r"recall|bankrupt|attack|fire|halt|shutdown|breach"
    )
    SEED = 42

    def _step(msg: str) -> None:
        progress(msg)
        sys.stdout.flush()

    df = _load_urgency_from_db()
    if df.empty:
        _step("Urgency table empty — pushing detected CSVs (ingest+clean)...")
        push_urgency()
        df = _load_urgency_from_db()
    if df.empty:
        raise RuntimeError("No urgency training rows after push.")

    _step(f"1/6 Loaded {len(df)} cleaned rows from ml_train_urgency")
    texts = (df["headline"].fillna("") + ". " + df["body"].fillna("")).to_numpy(dtype=object)
    y = df["priority"].map({label: i for i, label in enumerate(LABELS)}).to_numpy(dtype=int)
    texts_train, texts_test, y_train, y_test = train_test_split(
        texts, y, test_size=0.2, stratify=y, random_state=SEED
    )
    _step(f"2/6 Split train/test — train={len(y_train)} test={len(y_test)}")

    def numeric_features(series_texts):
        s = pd.Series(list(series_texts))
        return np.c_[
            s.str.len().values / 500.0,
            s.str.count(URG_WORDS, flags=re.I).values,
            s.str.contains(r"\d").astype(int).values,
            s.str.count(r"[A-Z]{4,}").values,
        ]

    def featurize(tfidf, series_texts, *, fit=False):
        matrix = tfidf.fit_transform(series_texts) if fit else tfidf.transform(series_texts)
        return hstack([matrix, csr_matrix(numeric_features(series_texts))]).tocsr()

    _step("3/6 Building TF-IDF features (this can take ~10–30s)...")
    t0 = time.perf_counter()
    tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, min_df=2, sublinear_tf=True)
    X_train = featurize(tfidf, texts_train, fit=True)
    X_test = featurize(tfidf, texts_test)
    _step(f"   Features ready in {time.perf_counter() - t0:.1f}s — shape={X_train.shape}")

    base = XGBClassifier(
        objective="multi:softprob",
        num_class=5,
        tree_method="hist",
        eval_metric="mlogloss",
        random_state=SEED,
        n_jobs=-1,
    )
    if fast:
        _step("4/6 Fitting XGBoost (fast mode, no CV search)...")
        t0 = time.perf_counter()
        model = base.set_params(n_estimators=200, max_depth=5, learning_rate=0.1)
        model.fit(X_train, y_train)
        _step(f"   Fit done in {time.perf_counter() - t0:.1f}s")
        print("Best params:", {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.1})
        print("CV macro F1: (skipped — fast mode)")
    else:
        _step(
            "4/6 Hyperparameter search (8 trials × 3-fold CV) — "
            "often 2–10+ minutes; please wait..."
        )
        t0 = time.perf_counter()
        search = RandomizedSearchCV(
            base,
            {
                "n_estimators": [200, 400],
                "max_depth": [3, 5, 7],
                "learning_rate": [0.05, 0.1, 0.2],
                "subsample": [0.8, 1.0],
                "colsample_bytree": [0.5, 0.8],
            },
            n_iter=8,
            scoring="f1_macro",
            cv=StratifiedKFold(3, shuffle=True, random_state=SEED),
            random_state=SEED,
            n_jobs=1,
            verbose=1,
        )
        search.fit(X_train, y_train)
        model = search.best_estimator_
        _step(f"   Search done in {time.perf_counter() - t0:.1f}s")
        print("Best params:", search.best_params_)
        print("CV macro F1:", round(float(search.best_score_), 4))

    _step("5/6 Evaluating on test set...")
    pred = model.predict(X_test)
    print("Accuracy:", round(float(accuracy_score(y_test, pred)), 4))
    print("Macro F1:", round(float(f1_score(y_test, pred, average="macro")), 4))
    print("Within 1 level:", round(float(np.mean(np.abs(pred - y_test) <= 1)), 4))
    print(classification_report(y_test, pred, target_names=LABELS, digits=3))
    print(pd.DataFrame(confusion_matrix(y_test, pred), index=LABELS, columns=LABELS))

    _step("6/6 Saving model artifact...")
    model_dir = ROOT / "artifacts" / "models" / "editor_queue_urgency"
    model_dir.mkdir(parents=True, exist_ok=True)
    art = model_dir / "model.joblib"
    metrics_path = model_dir / "metrics.json"
    payload_metrics = {
        "accuracy": float(accuracy_score(y_test, pred)),
        "macro_f1": float(f1_score(y_test, pred, average="macro")),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
    }
    joblib.dump(
        {
            "model": model,
            "model_name": "XGBoost",
            "tfidf": tfidf,
            "labels": LABELS,
            "urg_regex": URG_WORDS,
        },
        art,
    )
    metrics_path.write_text(json.dumps(payload_metrics, indent=2), encoding="utf-8")
    _step(f"Saved {art}")
    _step(f"Saved {metrics_path}")
    return payload_metrics


def train_cae_from_db() -> dict:
    import sys

    from ml.adaptation.training import train_all_from_dataframe
    from utils.progress import progress

    df = _load_adaptation_from_db()
    if df.empty:
        progress("CAE table empty — pushing detected CSVs (ingest+clean)...")
        sys.stdout.flush()
        push_adaptation()
        df = _load_adaptation_from_db()
    if df.empty:
        raise RuntimeError("No adaptation training rows after push.")
    progress(f"Training unified CAE from DB ({len(df)} rows) — building features + fit...")
    sys.stdout.flush()
    return train_all_from_dataframe(df)


def _cae_summary(cae_results: dict) -> dict:
    block = cae_results.get("content_adaptation") or cae_results
    metrics = (block.get("metrics") or {}).get("test") or {}
    per = block.get("per_platform") or {}
    out: dict = {
        "unified": {
            "test_f1": metrics.get("f1"),
            "test_accuracy": metrics.get("accuracy"),
        }
    }
    for platform, result in per.items():
        out[platform] = {
            "test_f1": result.get("f1"),
            "test_accuracy": result.get("accuracy"),
        }
    return out


def _write_train_summary(summary: dict) -> None:
    if not summary:
        return
    out = ROOT / "artifacts" / "models" / "training_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print()
    print(json.dumps(summary, indent=2))
    print("wrote", out)


def train_all(*, fast: bool = False) -> dict:
    """Push (ingest+clean) urgency + CAE datasets; train urgency and CAE."""
    push_urgency()
    push_adaptation()
    summary: dict = {
        "editor_queue_urgency": train_urgency_from_db(fast=fast),
        "cae_adaptation": _cae_summary(train_cae_from_db()),
    }
    _write_train_summary(summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NewsMind trainer (ML CSV → ingest+clean → DB → train)"
    )
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--urgency", action="store_true")
    parser.add_argument("--cae", action="store_true")
    parser.add_argument("--push-only", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-push even if file hash unchanged")
    parser.add_argument("--file", default="", help="Specific CSV filename under the dataset folder")
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    if not any([args.all, args.urgency, args.cae, args.push_only]):
        parser.print_help()
        raise SystemExit(1)

    file_arg = args.file or None

    if args.all:
        if file_arg:
            raise SystemExit("--file cannot be combined with --all")
        train_all(fast=args.fast)
        return

    summary: dict = {}
    if args.push_only or args.urgency:
        push_urgency(file_arg, force=args.force)
    if args.push_only or args.cae:
        push_adaptation(file_arg, force=args.force)

    if args.push_only:
        print("Push complete.")
        return

    if args.urgency:
        summary["editor_queue_urgency"] = train_urgency_from_db(fast=args.fast)
    if args.cae:
        summary["cae_adaptation"] = _cae_summary(train_cae_from_db())

    _write_train_summary(summary)


if __name__ == "__main__":
    main()
