"""Journalist intelligence services (research, evidence, metadata, etc.)."""

from services.journalist.content_validate import validate_article
from services.journalist.credibility import assess_credibility
from services.journalist.duplicate_check import find_duplicates
from services.journalist.evidence_search import search_evidence
from services.journalist.metadata import extract_metadata
from services.journalist.patent_search import search_patents
from services.journalist.research import search_related_news

__all__ = [
    "search_related_news",
    "search_evidence",
    "extract_metadata",
    "find_duplicates",
    "validate_article",
    "assess_credibility",
    "search_patents",
]
