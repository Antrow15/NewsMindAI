"""TF-IDF + cosine ranking and near-duplicate checks (shared)."""

from __future__ import annotations

from collections import Counter
from math import log
from typing import Any, Mapping, Sequence

import numpy as np

from ml.common.text import normalize, word_ngrams


def _tokens(text: str) -> list[str]:
    return normalize(text).split()


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _doc_text(doc: Mapping[str, Any]) -> str:
    return str(doc.get("text") or doc.get("content_body") or doc.get("body") or doc.get("title") or "")


def _tfidf_matrix(
    query_tokens: Sequence[str],
    doc_tokens: Sequence[Sequence[str]],
) -> tuple[np.ndarray, list[np.ndarray]]:
    """Build smoothed TF-IDF vectors for query + docs (shared IDF over the corpus)."""
    corpus = [list(query_tokens), *[list(toks) for toks in doc_tokens]]
    vocab_terms = sorted({t for tokens in corpus for t in tokens})
    if not vocab_terms:
        empty = np.zeros(0, dtype=float)
        return empty, [empty for _ in doc_tokens]

    vocab = {term: i for i, term in enumerate(vocab_terms)}
    n_docs = len(doc_tokens)
    df = Counter()
    for tokens in doc_tokens:
        df.update(set(tokens))

    idf = np.zeros(len(vocab), dtype=float)
    for term, idx in vocab.items():
        # smoothed IDF: log((N+1)/(df+1)) + 1
        idf[idx] = log((n_docs + 1) / (df.get(term, 0) + 1)) + 1.0

    def tfidf_vec(tokens: Sequence[str]) -> np.ndarray:
        vec = np.zeros(len(vocab), dtype=float)
        if not tokens:
            return vec
        counts = Counter(tokens)
        length = float(len(tokens))
        for term, count in counts.items():
            idx = vocab.get(term)
            if idx is None:
                continue
            tf = count / length
            vec[idx] = tf * idf[idx]
        return vec

    q_vec = tfidf_vec(query_tokens)
    d_vecs = [tfidf_vec(toks) for toks in doc_tokens]
    return q_vec, d_vecs


def rank(
    query: str,
    documents: Sequence[Mapping[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Rank documents by TF-IDF + cosine similarity to the query.

    Each document may include id, title, text (or content_body / body).
    Empty corpus → [].
    """
    docs = list(documents or [])
    if not docs or not normalize(query):
        return []

    query_tokens = _tokens(query)
    doc_tokens = [_tokens(_doc_text(d)) for d in docs]
    q_vec, d_vecs = _tfidf_matrix(query_tokens, doc_tokens)
    if q_vec.size == 0:
        return []

    scored: list[dict[str, Any]] = []
    for doc, d_vec in zip(docs, d_vecs):
        score = _cosine(q_vec, d_vec)
        if score <= 0:
            continue
        scored.append(
            {
                "id": doc.get("id") or doc.get("kb_id") or doc.get("content_id") or doc.get("evidence_id"),
                "title": doc.get("title") or "",
                "score": round(score, 4),
                "source_tag": doc.get("source_tag") or doc.get("category") or "",
            }
        )

    scored.sort(key=lambda row: row["score"], reverse=True)
    return scored[: max(0, int(limit))]


def _minhash_signature(text: str, *, num_hashes: int = 32) -> set[int]:
    """Simple hash-shingle signature for near-duplicate detection."""
    shingles = word_ngrams(text, n=3) or _tokens(text)
    if not shingles:
        return set()
    sig: set[int] = set()
    for i in range(num_hashes):
        best = min(hash((i, s)) & 0xFFFFFFFF for s in shingles)
        sig.add(best)
    return sig


def _jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def similar_pairs(
    documents: Sequence[Mapping[str, Any]],
    *,
    threshold: float = 0.5,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Find near-duplicate pairs using MinHash-style Jaccard on shingles."""
    docs = list(documents or [])
    if len(docs) < 2:
        return []

    sigs = [_minhash_signature(_doc_text(d)) for d in docs]
    pairs: list[dict[str, Any]] = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            score = _jaccard(sigs[i], sigs[j])
            if score < threshold:
                continue
            pairs.append(
                {
                    "left_id": docs[i].get("id") or docs[i].get("content_id"),
                    "right_id": docs[j].get("id") or docs[j].get("content_id"),
                    "left_title": docs[i].get("title") or "",
                    "right_title": docs[j].get("title") or "",
                    "score": round(score, 4),
                }
            )

    pairs.sort(key=lambda row: row["score"], reverse=True)
    return pairs[: max(0, int(limit))]
