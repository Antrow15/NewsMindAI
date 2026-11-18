# Naming guide (keep it simple)

This is a college project. Names should say **what** something is.

## Two different “priority” ideas (do not mix them)

| Name in code | Who uses it | Meaning |
|--------------|-------------|---------|
| **Editor queue urgency** | Editor / Manager | How soon should this story be reviewed? (`urgent` / `high` / `medium` / `low`) |
| **Pitch importance** | AIA story pitches | How important is this pitch idea? Simple formula. Stored in DB column `story_pitch.priority` |

- Dataset: `ml/editor/dataset/synthetic_news.csv`
- Model file: `artifacts/models/editor_queue_urgency.joblib`
- Function: `predict_editor_queue_urgency(...)`
- API field on content queue: `editor_queue_urgency`

Pitch responses use `pitch_importance` (and still write the DB column named `priority`).

## News vs article vs story pitch (do not mix)

| Thing | What it is | DB |
|-------|------------|-----|
| **News** | Event / breaking-style piece | `content` + `news` (`content_kind = news`) |
| **Article** | Feature / longer story | `content` + `article` (`content_kind = article`) |
| **Story pitch** | Idea *before* writing — meant for an **article** | `story_pitch` → later linked via `article.story_pitch_id` |

Story pitches are **not** for the `news` kind. The schema already links pitches to `article`, not to `news`.

## Flags vs topics (different things)

| Field | Where | Meaning |
|-------|-------|---------|
| `breaking_news_flag` | `news` table | Only boolean “flag” for news: is this breaking? |
| `severity` | `news` table | low / medium / high / critical (not a flag) |
| `content_kind` | `content` table | `news` or `article` |
| **topic / category** | Manual entry + `category` table | Politics, Sports, Business, … — **not flags**, **not a trained model** |

So: **Sports / Politics / Weather are categories (topics), not flags.**  
The only news boolean flag in the schema is **`breaking_news_flag`**.

## Content adaptation (CAE)

One shared model for all platforms: `artifacts/models/cae/`.  
Platform still matters at predict time (sentence limits + thresholds).

## Other clear names

| Name | Meaning |
|------|---------|
| `engagement_score` | Rough “will people interact?” score (formula) |
| `audience_interest_score` | Rough interest intensity (formula) |
| `trend_score` | Rough trendiness (formula) |
| `source_type` | `AI_GENERATED` (AIA) vs `MANUAL` |

## Layer names

| Folder | Job in one line |
|--------|-----------------|
| `api/schemas/` | JSON shapes for HTTP |
| `api/routers/` | HTTP endpoints |
| `modules/` | Thin desk façade (login user + call a service) |
| `services/` | Real business logic |
| `ml/` | Scoring + training (urgency, CAE, knowledge, AIA formulas) |
| `artifacts/models/` | Saved joblib models |
