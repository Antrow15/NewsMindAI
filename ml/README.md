# `ml/` — models and scoring

Everything ML lives here (no separate `ML project/` folder).

```
ml/
  common/          shared text + similarity + NER
  aia/             engagement / interest / trend formulas
  editor/          queue urgency model + dataset/
  adaptation/      unified CAE train + predict
  knowledge/       knowledge-base relevancy (journalist related-content)
  training/        console trainer: CSV → ml_train_* → artifacts/models
```

| Package | Main entry | Meaning |
|---------|------------|---------|
| `ml.editor` | `predict_editor_queue_urgency` | Editor review urgency |
| `ml.adaptation` | `predict_sentences` / `train_all_from_dataframe` | One CAE model, all platforms |
| `ml.aia` | `predict_engagement`, `predict_interest`, `predict_trend` | Formulas (no category model) |
| `ml.knowledge` | `score_content_relevancy` | Related news while drafting |
| `ml.training` | `train_all`, `train_urgency_from_db`, `train_cae_from_db` | Admin/console training |

**Active trained models (2):**

1. `artifacts/models/editor_queue_urgency.joblib` — dataset: `ml/editor/dataset/synthetic_news.csv`
2. `artifacts/models/cae/` — pairs: `data/adaptation/newsmind_paired_examples.csv`

Train: Admin console **ML TRAINING**, or `python -m ml.training --all`.

Category is **manual entry** (no model). Naming notes: `docs/NAMING.md`.
