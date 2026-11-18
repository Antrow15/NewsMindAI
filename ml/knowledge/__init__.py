"""Relevancy helpers — TF-IDF + cosine over desk-published ``content``."""

from ml.knowledge.base import (
    cleanup_legacy_relevancy_sources,
    load_published_documents,
    score_content_relevancy,
)

__all__ = [
    "cleanup_legacy_relevancy_sources",
    "load_published_documents",
    "score_content_relevancy",
]
