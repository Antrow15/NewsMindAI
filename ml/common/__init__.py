"""Shared text / similarity / NER helpers (no desk-specific models)."""

from ml.common.entities import extract_entities
from ml.common.similarity import rank, similar_pairs
from ml.common.text import normalize, word_ngrams

__all__ = [
    "normalize",
    "word_ngrams",
    "rank",
    "similar_pairs",
    "extract_entities",
]
