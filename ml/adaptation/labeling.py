"""Build sentence retain/reject labels from paired original ↔ adapted articles."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ml.adaptation.sentences import context_window, split_sentences

STRONG_POSITIVE_THRESHOLD = 0.50
NEGATIVE_THRESHOLD = 0.20
MAX_POSITIVE_SENTENCES = {
    "SOCIAL_MEDIA": 3,
    "EMAIL_NEWSLETTER": 6,
    "PRINT_NEWSPAPER": 9,
    "WEBSITE": 11,
}
MIN_POSITIVE_SENTENCES = {
    "SOCIAL_MEDIA": 1,
    "EMAIL_NEWSLETTER": 2,
    "PRINT_NEWSPAPER": 3,
    "WEBSITE": 4,
}


def _create_similarity_matrix(
    source_sentences: list[str],
    target_sentences: list[str],
) -> np.ndarray:
    corpus = source_sentences + target_sentences
    word_vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    character_vectorizer = TfidfVectorizer(
        lowercase=True,
        analyzer="char_wb",
        ngram_range=(3, 5),
        sublinear_tf=True,
    )
    word_matrix = word_vectorizer.fit_transform(corpus)
    character_matrix = character_vectorizer.fit_transform(corpus)
    source_count = len(source_sentences)
    word_similarity = cosine_similarity(word_matrix[:source_count], word_matrix[source_count:])
    character_similarity = cosine_similarity(
        character_matrix[:source_count], character_matrix[source_count:]
    )
    return 0.70 * word_similarity + 0.30 * character_similarity


def _select_positive_indexes(similarity_matrix: np.ndarray, platform: str) -> set[int]:
    source_count, target_count = similarity_matrix.shape
    if source_count == 0 or target_count == 0:
        return set()

    maximum_scores = similarity_matrix.max(axis=1)
    selected_indexes: set[int] = set()
    for target_index in range(target_count):
        selected_indexes.add(int(np.argmax(similarity_matrix[:, target_index])))
    for source_index, score in enumerate(maximum_scores):
        if score >= STRONG_POSITIVE_THRESHOLD:
            selected_indexes.add(source_index)

    minimum_count = min(MIN_POSITIVE_SENTENCES.get(platform, 1), source_count)
    maximum_count = min(MAX_POSITIVE_SENTENCES.get(platform, max(1, target_count)), source_count)
    ranked_indexes = np.argsort(maximum_scores)[::-1].tolist()
    for source_index in ranked_indexes:
        if len(selected_indexes) >= minimum_count:
            break
        selected_indexes.add(int(source_index))
    if len(selected_indexes) > maximum_count:
        selected_indexes = set(
            sorted(selected_indexes, key=lambda i: maximum_scores[i], reverse=True)[
                :maximum_count
            ]
        )
    return selected_indexes


def build_sentence_records(row: dict[str, Any]) -> list[dict[str, Any]]:
    source_sentences = split_sentences(str(row["original_content"]))
    target_sentences = split_sentences(str(row["correct_adapted_article"]))
    if not source_sentences or not target_sentences:
        return []

    similarity_matrix = _create_similarity_matrix(source_sentences, target_sentences)
    maximum_scores = similarity_matrix.max(axis=1)
    positive_indexes = _select_positive_indexes(
        similarity_matrix, str(row["target_platform"])
    )

    records: list[dict[str, Any]] = []
    for position, sentence in enumerate(source_sentences):
        records.append(
            {
                "article_id": str(row["article_id"]),
                "platform": str(row["target_platform"]),
                "headline": str(row["original_title"]),
                "sentence": sentence,
                "context": context_window(source_sentences, position),
                "position": position,
                "total_sentences": len(source_sentences),
                "label": 1 if position in positive_indexes else 0,
                "label_similarity": float(maximum_scores[position]),
            }
        )
    return records
