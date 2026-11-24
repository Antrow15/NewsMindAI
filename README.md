# NewsMind

Console newsroom backend, FastAPI role APIs (Swagger at `/docs`), and Streamlit frontend.

## Architecture

| Layer | Path | Responsibility |
|---|---|---|
| Streamlit UI | `frontend/` | Role dashboards and desk features (HTTP + JWT) |
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
| Location | Push target | Used for |
|---|---|---|
| `data/raw/` | **`content`** via admin ingest | Desk workflow |
| `ml/editor/dataset/*.csv` | **`ml_train_urgency`** | Urgency model training |
| `ml/adaptation/dataset/*.csv` | **`ml_train_adaptation`** | CAE model training |
| `artifacts/models/…` | (trained artifacts) | Inference |

**Relevancy:** TF-IDF + cosine over **desk-published** `content` only (after publisher sets `status=published`). No history CSV corpus.

**Evidence flow:** create news/article with evidence → validate → `POST /journalist/credibility` with `content_id`.

**Push commands:** console *Push urgency* / *Push CAE*, or `python -m ml.training --push-only`.

---

## Config

Copy `ENV.example` → `.env`.  
`config/db_config.py` + `config/runtime.py` load it automatically.

Auth uses **JWT** (HS256) access tokens returned as `session_token`.  
`NEWSROOM_JWT_SECRET` is **required** in `.env` (no hardcoded secret in code). Logout revokes the token `jti` in-process until expiry.

Database bootstrap is a single file: `database/newsmind.sql` (`python app.py --init-db`).

Temp desk/probe data (metro stories, evidence, pitches): `database/seed_temp_data.sql` — run after init-db:

```powershell
python -c "from pathlib import Path; from database.connection import apply_sql_file; apply_sql_file(Path('database/seed_temp_data.sql'))"
```

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

Open **http://127.0.0.1:8000/docs** for Swagger.

### Streamlit frontend

Frontend from teammate fork (`dark-sriram/NewsMindAI`). With the API running on port 8000:

```powershell
cd "G:\NewsMind AI\NewsMindAI V2"
$env:PYTHONPATH = "G:\NewsMind AI\NewsMindAI V2"
# optional: $env:NEWSMIND_API_URL = "http://127.0.0.1:8000"
streamlit run frontend/app.py
```

Open **http://localhost:8501** and sign in with a demo login below.

### Demo logins

| Username | Password |
|---|---|
| `admin` | `Admin@NewsMind2026!` |
| `journalist` | `Journalist@NewsMind2026!` |
| `journalist2` | `Journalist@NewsMind2026!` (City desk) |
| `journalist3` | `Journalist@NewsMind2026!` (Politics desk) |
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
