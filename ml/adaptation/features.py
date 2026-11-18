"""Sentence features for the unified CAE retention model (TF-IDF + manual + platform)."""

from __future__ import annotations

import re

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MaxAbsScaler

from config.constants import ADAPTATION_PLATFORMS

NEGATION = re.compile(r"\b(no|not|never|neither|without)\b", re.I)
UNCERTAINTY = re.compile(
    r"\b(may|might|could|expected|likely|possible|estimated)\b", re.I
)
ATTRIBUTION = re.compile(r"\b(said|stated|reported|announced|according)\b", re.I)
CONDITION = re.compile(
    r"\b(if|unless|subject to|provided|depending|after approval)\b", re.I
)
CONTRAST = re.compile(r"\b(but|however|although|despite|while)\b", re.I)
NUMBER = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")
PERCENT = re.compile(r"(?:\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s+percent)", re.I)
CURRENCY = re.compile(
    r"(?:₹|\$|£|€)\s*\d|\b\d+(?:\.\d+)?\s*(?:crore|lakh|million|billion)\b", re.I
)
DATE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2}\b",
    re.I,
)


def numeric_features(records: list[dict]) -> np.ndarray:
    rows = []
    for r in records:
        s = r["sentence"]
        i = r["position"]
        n = max(r["total_sentences"] - 1, 1)
        platform = str(r.get("platform") or "").upper()
        one_hot = [1.0 if platform == code else 0.0 for code in ADAPTATION_PLATFORMS]
        rows.append(
            [
                i / n,
                len(s.split()),
                int(i == 0),
                int(i == 1),
                bool(NUMBER.search(s)),
                bool(PERCENT.search(s)),
                bool(CURRENCY.search(s)),
                bool(DATE.search(s)),
                int('"' in s or "“" in s),
                bool(NEGATION.search(s)),
                bool(UNCERTAINTY.search(s)),
                bool(ATTRIBUTION.search(s)),
                bool(CONDITION.search(s)),
                bool(CONTRAST.search(s)),
                *one_hot,
            ]
        )
    return np.asarray(rows, dtype=float)


class SentenceFeatureExtractor(BaseEstimator, TransformerMixin):
    def __init__(self, max_word_features: int = 30000, max_char_features: int = 20000):
        self.max_word_features = max_word_features
        self.max_char_features = max_char_features
        self.word = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.98,
            sublinear_tf=True,
            max_features=max_word_features,
        )
        self.char = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1,
            sublinear_tf=True,
            max_features=max_char_features,
        )
        self.scaler = MaxAbsScaler()

    def fit(self, X, y=None):
        contexts = [r["context"] for r in X]
        self.word.fit(contexts)
        self.char.fit(contexts)
        self.scaler.fit(numeric_features(X))
        return self

    def transform(self, X):
        contexts = [r["context"] for r in X]
        a = self.word.transform(contexts)
        b = self.char.transform(contexts)
        c = csr_matrix(self.scaler.transform(numeric_features(X)))
        return hstack([a, b, c], format="csr")
