"""Journalist knowledge base — historical/current news for research & relevancy."""

from ml.knowledge.base import (
    ensure_knowledge_base_loaded,
    load_knowledge_documents,
    score_content_relevancy,
)

__all__ = [
    "ensure_knowledge_base_loaded",
    "load_knowledge_documents",
    "score_content_relevancy",
]
