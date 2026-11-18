"""Content adaptation helpers (CAE) — sentence select, format, fact checks."""

from ml.adaptation.platforms import format_output
from ml.adaptation.predict import predict_sentences
from ml.adaptation.sentences import split_sentences
from ml.adaptation.validate import validate_facts

__all__ = [
    "split_sentences",
    "predict_sentences",
    "format_output",
    "validate_facts",
]
