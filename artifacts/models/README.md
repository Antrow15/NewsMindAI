# Saved models

| File / folder | Meaning | Used by |
|---------------|---------|---------|
| `editor_queue_urgency.joblib` | How urgent for editor review queue | `/editor/queue`, `/editor/queue/score` |
| `cae/model.joblib` + `metadata.json` | **One** content-adaptation model for all platforms | `/cae/adaptations` |

Active models: **2** — editor urgency + unified CAE.

Platform differences at predict time: sentence limits + per-platform thresholds in `cae/metadata.json` (`platform_thresholds`). Category suggestion was removed (manual entry).

Engagement + interest = formulas in code (`ml/aia/`), not joblib files.

Train via Admin console **ML TRAINING** menu or `python -m ml.training` / `scripts/train_models_console.py` (urgency + CAE + knowledge base; not from `content` table).

See `docs/NAMING.md`.
