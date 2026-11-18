"""One shared place for TF-style ranking and near-duplicate checks.

Uses plain term counts + cosine (numpy). No separate copy in each service.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

import numpy as np

from ml.common.text import normalize, word_ngrams


def _tokens(text: str) -> list[str]:
    return normalize(text).split()


def _tf_vector(tokens: Sequence[str], vocab: dict[str, int]) -> np.ndarray:
    vec = np.zeros(len(vocab), dtype=float)
    if not tokens:
        return vec
    counts = Counter(tokens)
    for term, count in counts.items():
        idx = vocab.get(term)
        if idx is not None:
            vec[idx] = float(count)
    return vec


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _doc_text(doc: Mapping[str, Any]) -> str:
    return str(doc.get("text") or doc.get("content_body") or doc.get("title") or "")


def rank(
    query: str,
    documents: Sequence[Mapping[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Rank documents by cosine similarity to query.

    Each document may include id, title, text (or content_body).
    Empty corpus → [].
    """
    docs = list(documents or [])
    if not docs or not normalize(query):
        return []

    query_tokens = _tokens(query)
    doc_tokens = [_tokens(_doc_text(d)) for d in docs]
    vocab_terms = sorted({t for tokens in [query_tokens, *doc_tokens] for t in tokens})
    if not vocab_terms:
        return []

    vocab = {term: i for i, term in enumerate(vocab_terms)}
    q_vec = _tf_vector(query_tokens, vocab)

    scored: list[dict[str, Any]] = []
    for doc, tokens in zip(docs, doc_tokens):
        score = _cosine(q_vec, _tf_vector(tokens, vocab))
        if score <= 0:
            continue
        scored.append(
            {
                "id": doc.get("id") or doc.get("content_id") or doc.get("evidence_id"),
                "title": doc.get("title") or "",
                "score": round(score, 4),
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
    """Find near-duplicate pairs using MinHash-style Jaccard on shingles.

    Empty / single-doc corpus → [].
    """
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
