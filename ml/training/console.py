"""Console model training: CSV → ``ml_train_*`` staging → train → artifacts.

The ``content`` table is never used for training data. Newsroom ingest uses
``ingest_file`` / ``raw_ingest``; ``ml_train_*`` tables hold training rows loaded
from CSVs (urgency, adaptation pairs, knowledge base seeds).
"""

from __future__ import annotations

import argparse
import json
import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

# Datasets live under ml/ (urgency) and data/adaptation (CAE pairs)
URGENCY_CSV = ROOT / "ml" / "editor" / "dataset" / "synthetic_news.csv"
ADAPTATION_CSV = ROOT / "data" / "adaptation" / "newsmind_paired_examples.csv"


def _ensure_schema() -> None:
    from database.connection import ensure_ml_training_schema

    ensure_ml_training_schema()


def push_urgency(csv_path: Path = URGENCY_CSV) -> int:
    from database.connection import db_cursor

    _ensure_schema()
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    df = pd.read_csv(csv_path)
    with db_cursor() as cur:
        cur.execute("TRUNCATE ml_train_urgency RESTART IDENTITY")
        for row in df.itertuples(index=False):
            cur.execute(
                """
                INSERT INTO ml_train_urgency (headline, body, source, priority)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    str(getattr(row, "headline", "")),
                    str(getattr(row, "body", "") or ""),
                    str(getattr(row, "source", "") or ""),
                    str(getattr(row, "priority", "")),
                ),
            )
        cur.execute("SELECT COUNT(*) AS n FROM ml_train_urgency")
        n = int((cur.fetchone() or {}).get("n") or 0)
    print(f"Pushed {n} urgency rows → ml_train_urgency")
    return n


def push_adaptation(csv_path: Path = ADAPTATION_CSV) -> int:
    from database.connection import db_cursor

    _ensure_schema()
    target = csv_path if csv_path.exists() else ADAPTATION_CSV
    if not target.exists():
        print("Building paired adaptation CSV first...")
        builder = ROOT / "scripts" / "build_adaptation_paired_csv.py"
        spec = importlib.util.spec_from_file_location("build_adaptation_paired_csv", builder)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        mod.main()
        target = ADAPTATION_CSV
    df = pd.read_csv(target)
    with db_cursor() as cur:
        cur.execute("TRUNCATE ml_train_adaptation RESTART IDENTITY")
        for row in df.to_dict("records"):
            cur.execute(
                """
                INSERT INTO ml_train_adaptation
                    (article_id, original_title, original_content, target_platform, correct_adapted_article)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    str(row["article_id"]),
                    str(row["original_title"]),
                    str(row["original_content"]),
                    str(row["target_platform"]),
                    str(row["correct_adapted_article"]),
                ),
            )
        cur.execute("SELECT COUNT(*) AS n FROM ml_train_adaptation")
        n = int((cur.fetchone() or {}).get("n") or 0)
    print(f"Pushed {n} adaptation rows → ml_train_adaptation")
    return n


def push_knowledge_base() -> int:
    from ml.knowledge.base import ensure_knowledge_base_loaded

    _ensure_schema()
    n = ensure_knowledge_base_loaded(force=True)
    print(f"Pushed {n} knowledge_base rows")
    return n


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
    """Train urgency using rows from DB; print classification report + confusion matrix."""
    import re

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

    LABELS = ["very low", "low", "medium", "high", "very high"]
    URG_WORDS = (
        r"urgent|breaking|critical|immediate|emergency|severe|ban|sanction|"
        r"recall|bankrupt|attack|fire|halt|shutdown|breach"
    )
    SEED = 42

    df = _load_urgency_from_db()
    if df.empty:
        push_urgency()
        df = _load_urgency_from_db()
    print(f"Training urgency from DB ({len(df)} rows)...")

    texts = (df["headline"].fillna("") + ". " + df["body"].fillna("")).to_numpy(dtype=object)
    y = df["priority"].map({label: i for i, label in enumerate(LABELS)}).to_numpy(dtype=int)
    texts_train, texts_test, y_train, y_test = train_test_split(
        texts, y, test_size=0.2, stratify=y, random_state=SEED
    )

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

    tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, min_df=2, sublinear_tf=True)
    X_train = featurize(tfidf, texts_train, fit=True)
    X_test = featurize(tfidf, texts_test)

    base = XGBClassifier(
        objective="multi:softprob",
        num_class=5,
        tree_method="hist",
        eval_metric="mlogloss",
        random_state=SEED,
        n_jobs=-1,
    )
    if fast:
        model = base.set_params(n_estimators=200, max_depth=5, learning_rate=0.1)
        model.fit(X_train, y_train)
        best_params = {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.1}
        print("Best params:", best_params)
        print("CV macro F1: (skipped --fast)")
    else:
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
        )
        search.fit(X_train, y_train)
        model = search.best_estimator_
        print("Best params:", search.best_params_)
        print("CV macro F1:", round(float(search.best_score_), 4))

    pred = model.predict(X_test)
    print("Accuracy:", round(float(accuracy_score(y_test, pred)), 4))
    print("Macro F1:", round(float(f1_score(y_test, pred, average="macro")), 4))
    print("Within 1 level:", round(float(np.mean(np.abs(pred - y_test) <= 1)), 4))
    print(classification_report(y_test, pred, target_names=LABELS, digits=3))
    print(pd.DataFrame(confusion_matrix(y_test, pred), index=LABELS, columns=LABELS))

    art = ROOT / "artifacts" / "models" / "editor_queue_urgency.joblib"
    art.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model,
        "model_name": "XGBoost",
        "tfidf": tfidf,
        "labels": LABELS,
        "urg_regex": URG_WORDS,
    }
    joblib.dump(payload, art)
    print("Saved", art)
    return {
        "accuracy": float(accuracy_score(y_test, pred)),
        "macro_f1": float(f1_score(y_test, pred, average="macro")),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
    }


def train_cae_from_db() -> dict:
    from ml.adaptation.training import train_all_from_dataframe

    df = _load_adaptation_from_db()
    if df.empty:
        push_adaptation()
        df = _load_adaptation_from_db()
    print(f"Training unified CAE model from DB ({len(df)} rows)...")
    return train_all_from_dataframe(df)


def _cae_summary(cae_results: dict) -> dict:
    """Normalize unified CAE train result for console_train_summary.json."""
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
    out = ROOT / "artifacts" / "models" / "console_train_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print()
    print(json.dumps(summary, indent=2))
    print("wrote", out)


def train_all(*, fast: bool = False) -> dict:
    """Push urgency + adaptation + KB CSVs; train urgency and CAE only (no category)."""
    push_urgency()
    push_adaptation()
    push_knowledge_base()
    summary: dict = {
        "editor_queue_urgency": train_urgency_from_db(fast=fast),
        "cae_adaptation": _cae_summary(train_cae_from_db()),
    }
    _write_train_summary(summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="NewsMind console model trainer (CSV → DB → train)")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Push + train urgency, unified CAE, and knowledge base",
    )
    parser.add_argument("--urgency", action="store_true")
    parser.add_argument("--cae", action="store_true")
    parser.add_argument("--knowledge", action="store_true", help="Push knowledge base CSVs to DB")
    parser.add_argument("--push-only", action="store_true", help="Only push CSVs to DB")
    parser.add_argument("--fast", action="store_true", help="Faster urgency training (no CV search)")
    args = parser.parse_args()

    if not any([args.all, args.urgency, args.cae, args.knowledge, args.push_only]):
        parser.print_help()
        raise SystemExit(1)

    if args.all:
        train_all(fast=args.fast)
        return

    summary: dict = {}
    if args.push_only or args.urgency:
        push_urgency()
    if args.push_only or args.cae:
        push_adaptation()
    if args.push_only or args.knowledge:
        push_knowledge_base()

    if args.push_only:
        print("Push complete.")
        return

    if args.urgency:
        summary["editor_queue_urgency"] = train_urgency_from_db(fast=args.fast)
    if args.cae:
        summary["cae_adaptation"] = _cae_summary(train_cae_from_db())

    _write_train_summary(summary)