# NewsMind

Console newsroom backend plus FastAPI role APIs (Swagger at `/docs`).

## Architecture

| Layer | Path | Responsibility |
|---|---|---|
| Console CLI | `app.py` | Role menus, human-readable output |
| FastAPI + Swagger | `api/` | Auth, journalist, AIA, CAE, publisher, editor, manager, admin |
| Feature modules | `modules/` | Auth, admin pipeline, content desk, journalist tools |
| Services | `services/` | Pipeline + desks |
| ML helpers | `ml/` | `common` + `aia` + `editor` + `adaptation` + `knowledge` + `training` |
| Cleaners | `cleaners/` | Shared ingest cleaning stages |
| DAO / Entities | `dao/`, `entities/` | Table access + domain objects |

## Data vs ML

| Location | Purpose |
|---|---|
| `data/news/`, `data/historical/` | Journalist **content relevance / related history** only (`knowledge_base` → related-content) |
| `data/raw/` | Newsroom ingest → `content` |
| `data/patents/` | Patent research corpus (not history/relevance) |
| `ml/editor/dataset/*.csv` | Urgency training (any filename) |
| `ml/adaptation/dataset/*.csv` | CAE training (any filename) |
| `artifacts/models/editor_queue_urgency/` | Urgency model (`model.joblib`, `metrics.json`) |
| `artifacts/models/cae/` | CAE model (`model.joblib`, `metadata.json`, `metrics.json`) |

**Evidence** is always attached to a news/article (`content_id`). Multiple items per content are allowed. No orphan evidence and no reusing another story’s evidence.

**ML training flow:** `ml/**/dataset/*.csv` → ingest/normalize → same cleaners → `ml_train_*` (skip if file hash unchanged) → train → `artifacts/models/`.

---

## Config

Copy `ENV.example` → `.env`.  
`config/db_config.py` + `config/runtime.py` load it automatically.

---

## Start

```powershell
cd "G:\NewsMind AI\NewsMindAI V2"
$env:PYTHONPATH = "G:\NewsMind AI\NewsMindAI V2"
python -m pip install -r requirements.txt
python app.py --init-db
python app.py
```

```powershell
$env:PYTHONPATH = "G:\NewsMind AI\NewsMindAI V2"
uvicorn api.main:app --reload
```

Open **http://127.0.0.1:8000/docs** or **http://127.0.0.1:8000/easy**

### Demo logins

| Username | Password |
|---|---|
| `admin` | `Admin@NewsMind2026!` |
| `journalist` | `Journalist@NewsMind2026!` |
| `editor` | `Editor@NewsMind2026!` |
| `publisher` | `Publisher@NewsMind2026!` |
| `manager` | `Manager@NewsMind2026!` |
| `analyst` | `Analyst@NewsMind2026!` |
| `adapter` | `Adapter@NewsMind2026!` |

### ML training

```powershell
python -m ml.training --push-only
python -m ml.training --all --fast
```

Admin console **ML TRAINING** auto-detects every `*.csv` under the dataset folders, pushes new/changed files (hash skip), then trains.
