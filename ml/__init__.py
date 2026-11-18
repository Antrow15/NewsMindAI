"""ML helpers used by services (no FastAPI / no SQL here).

ml/common/      shared text + similarity + NER
ml/aia/         audience scores (engagement/interest/trend)
ml/editor/      editor queue urgency
ml/adaptation/  CAE platform adaptations
ml/knowledge/   knowledge base relevancy for journalist drafting
ml/training/    console training (ingest staging → fit; never content table)
"""

from ml.aia import predict_engagement, predict_interest, predict_trend
from ml.common import extract_entities, normalize, rank, similar_pairs, word_ngrams
from ml.editor import model_available, predict_editor_queue_urgency

__all__ = [
    "normalize",
    "word_ngrams",
    "rank",
    "similar_pairs",
    "extract_entities",
    "predict_editor_queue_urgency",
    "model_available",
    "predict_engagement",
    "predict_interest",
    "predict_trend",
]
