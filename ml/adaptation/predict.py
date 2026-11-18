"""Select sentences for a target platform using the unified CAE model."""

from __future__ import annotations

from config.constants import PLATFORM_SENTENCE_LIMITS
from ml.adaptation.model_loader import load_model
from ml.adaptation.sentences import split_sentences
from utils.errors import ValidationError

DEPENDENT_STARTERS = ("however", "but", "therefore", "this", "they", "it", "he", "she", "although")


def predict_sentences(
    title: str,
    content: str,
    platform: str,
    threshold_delta: float = 0.0,
    sentence_delta: int = 0,
    prioritize_quotes: bool = False,
    prioritize_numbers: bool = False,
) -> tuple[list[tuple[int, str, float]], dict, float]:
    sentences = split_sentences(content)
    if not sentences:
        raise ValidationError("No valid sentences found in original content.")

    try:
        model, meta = load_model(platform)
    except FileNotFoundError as exc:
        raise ValidationError(str(exc)) from exc

    platform_key = str(platform).upper()
    records = []
    for i, sentence in enumerate(sentences):
        prev = sentences[i - 1] if i > 0 else ""
        nxt = sentences[i + 1] if i + 1 < len(sentences) else ""
        records.append(
            {
                "headline": title,
                "sentence": sentence,
                "context": f"PREVIOUS {prev} CURRENT {sentence} NEXT {nxt}",
                "position": i,
                "total_sentences": len(sentences),
                "platform": platform_key,
            }
        )
    probabilities = [float(p) for p in model.predict_proba(records)[:, 1]]

    platform_thresholds = meta.get("platform_thresholds") or {}
    base = float(
        platform_thresholds.get(platform_key, meta.get("threshold", 0.5))
    )
    threshold = max(0.05, min(0.95, base + threshold_delta))
    model_version = str(meta.get("version", "1.0.0"))

    scored: list[tuple[int, str, float]] = []
    for i, (sentence, prob) in enumerate(zip(sentences, probabilities)):
        boost = 0.0
        if prioritize_quotes and ('"' in sentence or "“" in sentence):
            boost += 0.15
        if prioritize_numbers and any(ch.isdigit() for ch in sentence):
            boost += 0.15
        scored.append((i, sentence, min(1.0, float(prob) + boost)))

    max_count = max(1, int(PLATFORM_SENTENCE_LIMITS.get(platform, 5)) + int(sentence_delta))
    selected = [row for row in scored if row[2] >= threshold]
    if not selected:
        selected = sorted(scored, key=lambda row: row[2], reverse=True)[:1]
    selected = sorted(selected, key=lambda row: row[2], reverse=True)[:max_count]

    indexes = {row[0] for row in selected}
    for i in list(indexes):
        if i > 0 and sentences[i].lower().startswith(DEPENDENT_STARTERS):
            indexes.add(i - 1)

    ordered = [(i, sentences[i], float(probabilities[i])) for i in sorted(indexes)]
    meta = {**meta, "version": model_version, "platform": platform_key}
    return ordered, meta, threshold
