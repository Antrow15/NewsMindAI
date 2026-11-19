"""Chapters 1–5 of the NewsMind V2 learning guide."""

from __future__ import annotations

from docx_helpers import bullet, code, h, note, numbered, p, table


def chapter_1(doc):
    h(doc, "1. Learning Goals for This Application", 1)

    h(doc, "1.1 What This Application Does", 2)
    p(
        doc,
        "NewsMind AI V2 is a newsroom operations backend. It models a real editorial desk: "
        "journalists create news and articles with evidence; editors review pitches and content "
        "using an ML urgency model; publishers release approved content; an Audience Insight "
        "Analyst (AIA) scores engagement and generates story pitches; a Content Adaptation "
        "Editor (CAE) adapts articles for social, print, web, and newsletter platforms; "
        "administrators run a CSV ingest → clean → persist ETL pipeline; and a newsroom manager "
        "sees operational analytics. The same business logic is exposed through a FastAPI HTTP "
        "API (Swagger at /docs, simple tester at /easy) and a console CLI (app.py).",
    )

    h(doc, "1.2 Problem It Solves", 2)
    bullet(doc, "Fragmented newsroom workflows across roles without shared data or permissions.")
    bullet(doc, "Manual triage of which story to review first (addressed by editor_queue_urgency).")
    bullet(doc, "Rewriting articles for every channel by hand (addressed by CAE sentence retention).")
    bullet(doc, "Ingesting messy CSV news corpora into a clean relational desk model.")
    bullet(doc, "Teaching / demoing a full-stack newsroom system with RBAC and ML hooks.")

    h(doc, "1.3 Why It Was Developed", 2)
    p(
        doc,
        "From README.md and code structure, V2 consolidates a console newsroom backend with "
        "role-based FastAPI APIs, shared cleaners, DAO/entity persistence, and ML helpers for "
        "urgency, adaptation, relevancy, and audience heuristics. It is an educational and "
        "operational prototype of a digital newsroom, not a generic CMS.",
    )

    h(doc, "1.4 Technologies Used", 2)
    table(
        doc,
        ["Technology", "Role in V2"],
        [
            ["Python 3", "Primary language"],
            ["FastAPI + Uvicorn", "HTTP API, OpenAPI/Swagger, static /easy UI"],
            ["Pydantic v2", "Request/response schemas and field validation"],
            ["PostgreSQL + psycopg2", "Relational store; RealDictCursor rows"],
            ["pandas / numpy / scipy", "CSV ingest and numeric/ML support"],
            ["scikit-learn + joblib", "TF-IDF, LogisticRegression CAE pipeline, artifacts"],
            ["XGBoost", "Editor queue urgency multi-class model"],
            ["spaCy (optional)", "Named-entity helpers with regex fallback"],
            ["httpx + pytest", "API TestClient and test suite"],
            ["stdlib hashlib/hmac/secrets", "PBKDF2 password hashing, session tokens"],
        ],
    )

    h(doc, "1.5 What You Will Learn", 2)
    numbered(doc, "Layered architecture: routers → modules/services → repositories → DAOs → SQL.")
    numbered(doc, "Capability-based RBAC without a separate permissions table.")
    numbered(doc, "JWT Bearer auth (HS256) with required NEWSROOM_JWT_SECRET; logout via jti denylist.")
    numbered(doc, "ETL pipeline design: hash-skip ingest, multi-stage cleaners, persistence.")
    numbered(doc, "How ML artifacts are trained offline and loaded at inference time.")
    numbered(doc, "How a single HTML page can exercise an entire role API surface.")

    h(doc, "1.6 Prerequisites", 2)
    bullet(doc, "Python fundamentals: modules, packages, dataclasses, typing, exceptions.")
    bullet(doc, "HTTP basics: methods, status codes, JSON bodies, Authorization headers.")
    bullet(doc, "SQL basics: tables, PK/FK, indexes, INSERT/SELECT/UPDATE.")
    bullet(doc, "Helpful but not required: FastAPI Depends, scikit-learn pipelines, newsroom vocabulary.")

    h(doc, "1.7 Outcomes After This Guide", 2)
    bullet(doc, "Explain the full request path for any role endpoint.")
    bullet(doc, "Trace content from CSV ingest to published status and AIA performance loop.")
    bullet(doc, "Add a new endpoint, field, or service method safely.")
    bullet(doc, "Debug auth failures, validation 422s, and missing ML model 503s.")
    bullet(doc, "Rebuild a similar newsroom system with the same patterns.")

    h(doc, "1.8 Learning Journey Map", 2)
    table(
        doc,
        ["Stage", "Focus", "Chapters"],
        [
            ["Beginner", "What the app is, folders, roles, env, startup", "1–3, 10"],
            ["Intermediate", "Endpoints, DB, validation, frontend bridge", "4–8, 11–12"],
            ["Advanced", "File-by-file code, ML, design trade-offs", "9, 13–16"],
            ["Mastery", "Exercises, glossary, assessment", "16–18"],
        ],
    )
    doc.add_page_break()


def chapter_2(doc):
    h(doc, "2. Complete Application Architecture", 1)

    h(doc, "2.1 Architecture Style", 2)
    p(
        doc,
        "V2 is a modular monolith: one Python process (API or CLI) with clear internal layers. "
        "It is not microservices. HTTP is optional—the console calls the same modules/services. "
        "Persistence uses the classic DAO pattern over raw SQL (not SQLAlchemy ORM). Domain "
        "objects are dataclasses in entities/. Business rules live in services/; feature façades "
        "with capability checks live in modules/.",
    )

    h(doc, "2.2 Architectural Layers", 2)
    table(
        doc,
        ["Layer", "Path", "Responsibility", "If removed"],
        [
            ["Presentation HTTP", "api/", "Routes, schemas, CORS, exception handlers", "No Swagger/easy UI"],
            ["Presentation CLI", "app.py", "Role menus, argparse pipeline commands", "No interactive console"],
            ["Feature modules", "modules/", "Capability gates + orchestration façades", "Routers would call services raw"],
            ["Services", "services/", "Business logic, ML orchestration", "No desk behavior"],
            ["Cleaners", "cleaners/", "In-memory ETL transform stages", "Dirty CSV → bad content rows"],
            ["ML", "ml/", "Urgency, CAE, AIA heuristics, TF-IDF", "Fallbacks or 503 on models"],
            ["Repository", "repository/", "Multi-table aggregates", "Services talk to many DAOs"],
            ["DAO", "dao/", "Per-table SQL", "No persistence"],
            ["Entities", "entities/", "Typed row payloads", "Dict-only inserts"],
            ["Config/Utils", "config/, utils/", "Env, constants, validators, logging", "Hardcoded chaos"],
            ["Database", "database/", "Connection, schema SQL, seeds", "No store"],
        ],
    )

    h(doc, "2.3 Request–Response Architecture", 2)
    p(doc, "Typical authenticated API call (actual layers that exist):")
    code(
        doc,
        "Client (easy.html / Swagger / httpx)\n"
        "  → FastAPI route (api/routers/*.py)\n"
        "  → Depends(get_session_token)  [api/deps.py]\n"
        "  → Pydantic body/query validation  [api/schemas]\n"
        "  → require_capability_session(...)  [services/access.py]\n"
        "  → Module or Service method\n"
        "  → Repository / DAO / ml.*\n"
        "  → PostgreSQL via db_cursor()\n"
        "  → response_model serialization\n"
        "  → JSON to client\n"
        "On failure: AppError hierarchy → raise_http_error → HTTP 4xx/5xx JSON {detail}",
    )

    h(doc, "2.4 Design Patterns Used", 2)
    bullet(doc, "Façade: JournalistModule, AdminModule wrap services behind capability checks.")
    bullet(doc, "DAO: BaseDAO + table DAOs encapsulate SQL.")
    bullet(doc, "Repository: ContentRepository.save_content_bundle coordinates content+article|news.")
    bullet(doc, "Dependency Injection (FastAPI): Depends(get_session_token), Depends(get_current_user).")
    bullet(doc, "Strategy / Pipeline: CleaningPipeline runs ordered BaseCleaner stages.")
    bullet(doc, "RBAC capability map: ROLE_CAPABILITIES dict instead of ACL tables.")
    bullet(doc, "Application service: EditorService, PublisherService, AIAService, AdaptationService.")

    h(doc, "2.5 Communication Between Components", 2)
    p(
        doc,
        "In-process Python imports only—no message bus. CLI and API share modules/services. "
        "API auth uses signed JWTs (PyJWT HS256). CLI stores the last JWT in logs/.session_token. "
        "Logout revokes jti in-process (_REVOKED_JTI). ML models load from artifacts/models via "
        "joblib with lru_cache. Diagram source: documentation/diagrams/01_architecture.mmd.",
    )

    h(doc, "2.6 External Services", 2)
    p(
        doc,
        "No cloud LLM APIs are called at runtime. External dependency is PostgreSQL. spaCy may "
        "use a local blank model + EntityRuler. CSV files under data/raw and ml/*/dataset are "
        "local inputs. Trained models are local joblib files.",
    )

    h(doc, "2.7 Frontend Architecture", 2)
    p(
        doc,
        "There is no React/Vue SPA. api/static/easy.html is a single-page role console served at "
        "GET /easy. It uses fetch(), localStorage for token/user/role, and a GROUPS config that "
        "maps UI forms to REST endpoints. Swagger UI is framework-provided at /docs.",
    )

    h(doc, "2.8 Data Flow Summary", 2)
    bullet(doc, "ETL: CSV → IngestionService → cleaners → PersistenceService → content tables.")
    bullet(doc, "Desk: journalist creates content+evidence → submit → editor approve → publisher publish.")
    bullet(doc, "AIA: metrics formulas + story_pitch rows; performance reads published content.")
    bullet(doc, "CAE: adaptation_requests → per-platform drafts → review → final_adaptations.")
    bullet(doc, "ML train: dataset CSV → ml_train_* tables → train → artifacts/models.")
    note(doc, "See documentation/diagrams/02_etl_pipeline.mmd and 03_newsroom_flow.mmd.")
    doc.add_page_break()


def chapter_3(doc):
    h(doc, "3. Every Folder and File Explained", 1)
    p(
        doc,
        "This chapter explains the organisation of NewsMindAI V2 from the project root. "
        "Generated folders (__pycache__, .pytest_cache, .git) and large binary artifacts are "
        "noted but not line-explained. Probe scripts (_probe_*.py) and ALL_FILES_DUMP.txt are "
        "development aids, not runtime product paths.",
    )

    h(doc, "3.1 Why This Structure", 2)
    p(
        doc,
        "The tree mirrors layers: api for HTTP, modules for role façades, services for logic, "
        "dao/entities for persistence, cleaners for ETL transforms, ml for offline/online ML, "
        "config/utils for cross-cutting concerns. Keeping cleaners and ml separate from services "
        "lets the same cleaners serve admin ingest and ML dataset push.",
    )

    h(doc, "3.2 Root Files", 2)
    table(
        doc,
        ["File", "Purpose", "Depends on / depended by"],
        [
            ["app.py", "Console CLI entry: menus, argparse, init-db", "modules, services, database"],
            ["README.md", "Quick start, roles, architecture table", "Humans"],
            ["requirements.txt", "Pinned/ranged Python deps", "pip install"],
            ["ENV.example", "Template for .env (no secrets committed ideally)", "config loaders"],
            [".env", "Local DB + pipeline settings (do not commit secrets)", "db_config, runtime"],
            [".gitignore", "Ignores caches, env, artifacts noise", "git"],
        ],
    )

    h(doc, "3.3 api/", 2)
    bullet(doc, "main.py — create_app(), lifespan load_dotenv, CORS, exception handlers, router include, /easy.")
    bullet(doc, "deps.py — HTTPBearer → get_session_token → get_current_user via resolve_session.")
    bullet(doc, "http_errors.py — maps AuthError/PermissionDenied/NotFound/Validation/AppError to HTTP.")
    bullet(doc, "routers/ — one router per role domain (auth, journalist, aia, cae, publisher, editor, manager, admin).")
    bullet(doc, "schemas/ — Pydantic models; rules.py shared Annotated types.")
    bullet(doc, "static/easy.html — browser tester UI.")

    h(doc, "3.4 modules/", 2)
    bullet(doc, "authentication/ — auth_service (login/JWT resolve), security (PBKDF2 + JWT create/decode).")
    bullet(doc, "admin/admin_module.py — ingest/clean/persist/pipeline orchestration.")
    bullet(doc, "journalist/journalist_module.py — tools + desk CRUD façade.")
    bullet(doc, "content/content_module.py — thin ContentService wrapper for console.")

    h(doc, "3.5 services/", 2)
    bullet(doc, "ingestion_service.py, persistence_service.py, report_service.py — ETL.")
    bullet(doc, "content/, user/, editor/, manager/, publisher/, aia/, adaptation/ — desks.")
    bullet(doc, "journalist/ — validate, credibility, duplicates, evidence_search.")
    bullet(doc, "access.py, permission_service.py — session + capability gates.")

    h(doc, "3.6 dao/, entities/, repository/", 2)
    p(
        doc,
        "entities hold dataclasses matching tables. dao classes execute SQL with BaseDAO.execute "
        "and RealDictCursor. repository aggregates multi-table writes (e.g., save_content_bundle "
        "creates Content then Article or News). newsroom_repository.py is a compatibility façade.",
    )

    h(doc, "3.7 cleaners/", 2)
    bullet(doc, "orchestrator.py — clean_content / clean_pitches, optional processed file writes.")
    bullet(doc, "pipeline.py — runs Text → Null → Duplicate → Schema stages.")
    bullet(doc, "stages/* — BaseCleaner implementations + CleanerResult.")
    bullet(doc, "quality_report.py — stage metrics for cleaning_report JSON.")

    h(doc, "3.8 ml/", 2)
    bullet(doc, "training/ — push CSV to ml_train_* and train urgency/CAE.")
    bullet(doc, "editor/queue_urgency.py — load XGB pipeline; predict urgency.")
    bullet(doc, "adaptation/ — label, features, train, predict, validate, platforms.")
    bullet(doc, "aia/audience_scores.py — heuristic engagement/interest/trend.")
    bullet(doc, "knowledge/base.py — published-content TF-IDF relevancy.")
    bullet(doc, "common/ — text normalize, rank, similar_pairs, entities.")

    h(doc, "3.9 database/, data/, artifacts/, config/, utils/, tests/", 2)
    bullet(doc, "database/newsmind.sql — full schema bootstrap (wipes public).")
    bullet(doc, "database/connection.py — get_connection, db_cursor, init_schema, apply_sql_file.")
    bullet(doc, "database/seed_demo_users.py — seven demo desks.")
    bullet(doc, "database/seed_temp_data.sql — optional metro probe/desk seed.")
    bullet(doc, "data/raw/ — admin CSV ingest source.")
    bullet(doc, "artifacts/models/ — joblib models for urgency and CAE.")
    bullet(doc, "config/ — constants, db_config, env_loader, runtime.")
    bullet(doc, "utils/ — validators, errors, logger, helpers, csv_fields, console_ui, progress.")
    bullet(doc, "tests/ — API + pipeline pytest suite with db_ready fixture.")

    h(doc, "3.10 Directory Tree (source-focused)", 2)
    code(
        doc,
        "NewsMindAI V2/\n"
        "  app.py\n"
        "  api/  (main, deps, http_errors, routers/, schemas/, static/easy.html)\n"
        "  modules/ (admin, authentication, content, journalist)\n"
        "  services/ (ingestion, persistence, report, access, permission,\n"
        "            content/, user/, editor/, manager/, publisher/, aia/,\n"
        "            adaptation/, journalist/)\n"
        "  repository/  dao/  entities/  cleaners/  ml/  config/  utils/\n"
        "  database/ (connection.py, newsmind.sql, seed_*.py/sql)\n"
        "  data/raw/  artifacts/models/  tests/  logs/\n"
        "  documentation/  ← this learning guide",
    )
    doc.add_page_break()


def chapter_4(doc):
    h(doc, "4. Technical Concepts in Depth", 1)

    h(doc, "4.1 FastAPI Application Factory", 2)
    p(
        doc,
        "create_app() in api/main.py builds a FastAPI instance with OpenAPI tags, lifespan, "
        "CORSMiddleware, custom exception handlers, and include_router calls. The module-level "
        "app = create_app() is what uvicorn loads: uvicorn api.main:app.",
    )
    code(
        doc,
        "@asynccontextmanager\n"
        "async def lifespan(_app: FastAPI):\n"
        "    load_dotenv()\n"
        "    log.info(\"NewsMind API started. Swagger: /docs\")\n"
        "    yield",
    )
    p(
        doc,
        "Why: ensures .env is loaded when the API process starts. If removed, DB settings may "
        "fall back to defaults only when other modules call load_dotenv themselves.",
    )

    h(doc, "4.2 Dependency Injection (Depends)", 2)
    p(
        doc,
        "FastAPI Depends injects shared values into route parameters. get_session_token reads "
        "HTTPAuthorizationCredentials from HTTPBearer(auto_error=False). If missing, raises 401. "
        "get_current_user depends on that token and calls resolve_session. This keeps auth "
        "orthogonal to each route body.",
    )

    h(doc, "4.3 Capability-Based RBAC", 2)
    p(
        doc,
        "Roles map to capability strings in config.constants.ROLE_CAPABILITIES. "
        "permission_service.has_capability returns True for all capabilities if role is "
        "administrator. require_capability_session resolves the session then require_capability. "
        "Why not a permissions table? The desk model is small and static; a dict keeps demos "
        "simple. Trade-off: changing rights requires a code deploy.",
    )

    h(doc, "4.4 JWT Access Tokens (HS256)", 2)
    p(
        doc,
        "Login issues a signed JWT via create_access_token (PyJWT, HS256). Claims include "
        "sub/user_id, username, role_code, iat, exp (SESSION_TTL_HOURS=12), jti, and type=access. "
        "NEWSROOM_JWT_SECRET must be set in .env — get_jwt_secret() raises if missing (no hardcoded "
        "fallback). resolve_session verifies signature/expiry, checks _REVOKED_JTI for logout, then "
        "reloads the user from Postgres. The API field name remains session_token for compatibility. "
        "CLI stores the last JWT in logs/.session_token.",
    )

    h(doc, "4.5 Password Hashing (PBKDF2)", 2)
    p(
        doc,
        "security.hash_password stores salt_hex$digest_hex in users.password_hash. "
        "pbkdf2_hmac sha256 with PASSWORD_HASH_ITERATIONS=120000. verify_password uses "
        "hmac.compare_digest to avoid timing leaks. Why stdlib? Zero extra crypto deps; matches "
        "ERD single hash column.",
    )

    h(doc, "4.6 DAO + RealDictCursor", 2)
    p(
        doc,
        "db_cursor opens a connection, yields a cursor with RealDictCursor so rows behave like "
        "dicts. BaseDAO.execute runs SQL with fetch one/all/none. This is explicit SQL control "
        "without an ORM. Runtime: each call opens and closes a connection (simple, not a pool).",
    )

    h(doc, "4.7 Cleaning Pipeline Pattern", 2)
    p(
        doc,
        "Each stage inherits BaseCleaner and returns CleanerResult(kept, rejected, stats). "
        "Order matters: text normalize before null checks; duplicates before schema; schema "
        "validates enums/dates/content rules. Stages are pure transforms—no DB writes.",
    )

    h(doc, "4.8 TF-IDF + Cosine Similarity", 2)
    p(
        doc,
        "ml.common.similarity.rank and similar_pairs vectorize documents with TF-IDF and score "
        "cosine similarity. Used for journalist related-content, duplicates, credibility evidence "
        "ranking, and knowledge-base relevancy over published content. Alternative: embeddings; "
        "chosen approach needs no GPU and trains nothing for relevancy.",
    )

    h(doc, "4.9 Editor Queue Urgency Model", 2)
    p(
        doc,
        "Trained offline from ml_train_urgency via XGBoost multiclass over TF-IDF + hand features. "
        "Inference: predict_editor_queue_urgency loads joblib bundle (model, tfidf, labels). Maps "
        "fine labels to desk urgencies urgent/high/medium/low. If artifact missing, fallback "
        "source is returned (and ValidationError paths may yield 503 for 'No trained model').",
    )

    h(doc, "4.10 CAE Sentence Retention Model", 2)
    p(
        doc,
        "Paired original/adapted articles are split into sentences; labels come from similarity to "
        "the adapted text. A LogisticRegression pipeline predicts keep/drop per sentence with "
        "platform limits (PLATFORM_SENTENCE_LIMITS). ReviewService can regenerate with remarks. "
        "This is extractive adaptation, not generative LLM rewriting.",
    )

    h(doc, "4.11 Pydantic Validation vs utils.validators", 2)
    p(
        doc,
        "API boundary uses Pydantic (api/schemas + rules.py Annotated types). Domain services and "
        "cleaners use utils.validators (require_title, require_body, validate_content_record). "
        "Both layers exist so CLI/ETL paths validate without HTTP schemas.",
    )

    h(doc, "4.12 Exception Hierarchy", 2)
    code(
        doc,
        "AppError\n"
        "  ValidationError\n"
        "  NotFoundError\n"
        "  AuthError\n"
        "  PermissionDeniedError\n"
        "AuthenticationError  # separate, in auth_service",
    )
    p(doc, "API maps these via exception handlers and raise_http_error to consistent JSON errors.")
    doc.add_page_break()


def chapter_5(doc):
    h(doc, "5. Keywords, Variables, Functions, and Classes", 1)
    p(
        doc,
        "This chapter teaches Python/FastAPI keywords and important symbols as they appear in V2, "
        "then walks major classes and functions. Later Chapter 14 expands file-by-file.",
    )

    h(doc, "5.1 Important Keywords in Context", 2)
    table(
        doc,
        ["Keyword / construct", "Where", "Why"],
        [
            ["from __future__ import annotations", "Most modules", "Postpone evaluation of type hints"],
            ["async def / await", "Exception handlers, lifespan", "FastAPI async interface (routes often sync)"],
            ["yield", "lifespan, db_cursor", "Context setup/teardown"],
            ["@dataclass", "entities/*", "Boilerplate-free row objects"],
            ["Depends(...)", "routers, deps", "Inject token/user"],
            ["try / except / raise / from", "All layers", "Map domain errors to HTTP"],
            ["with", "db_cursor, file IO", "Guarantee close"],
            ["| None / Optional", "Signatures", "Explicit nullable types"],
            ["*", "Keyword-only args", "Force named params (e.g., only_new=)"],
            ["@router.post/get/put", "routers", "Register HTTP operations"],
            ["@lru_cache", "ML loaders", "Load model once per process"],
            ["frozen=True dataclass", "DatabaseConfig", "Immutable config"],
        ],
    )

    h(doc, "5.2 Critical Variables", 2)
    bullet(doc, "_REVOKED_JTI — process-local denylist of logged-out JWT ids until exp.")
    bullet(doc, "SESSION_FILE — Path logs/.session_token; CLI last JWT JSON.")
    bullet(doc, "NEWSROOM_JWT_SECRET / get_jwt_secret() — required signing secret from .env.")
    bullet(doc, "ROLE_CAPABILITIES — static role→capability mapping; source of truth for RBAC.")
    bullet(doc, "OPENAPI_TAGS — orders Swagger sections for learning UX.")
    bullet(doc, "STATIC_DIR — Path to api/static for FileResponse easy.html.")
    bullet(doc, "SCHEMA_SQL — Path database/newsmind.sql for init_schema.")

    h(doc, "5.3 Core Functions (selected)", 2)
    table(
        doc,
        ["Function", "File", "Role"],
        [
            ["authenticate(username, password)", "auth_service.py", "Verify hash, create JWT, return payload"],
            ["resolve_session(token)", "auth_service.py", "Verify JWT + denylist → user payload"],
            ["create_access_token(...)", "security.py", "Sign HS256 JWT claims"],
            ["decode_access_token(token)", "security.py", "Verify JWT signature/claims"],
            ["get_jwt_secret()", "constants.py", "Require NEWSROOM_JWT_SECRET from .env"],
            ["require_capability_session(cap, token)", "access.py", "Auth + RBAC gate"],
            ["raise_http_error(exc)", "http_errors.py", "Always raises HTTPException"],
            ["load_dotenv()", "env_loader.py", "Parse .env into os.environ once"],
            ["db_cursor()", "connection.py", "Context manager for RealDictCursor"],
            ["init_schema()", "connection.py", "Apply SQL + seed demo users"],
            ["validate_article(record)", "content_validate.py", "Field + relevancy report"],
            ["predict_editor_queue_urgency(...)", "queue_urgency.py", "ML urgency inference"],
            ["predict_sentences(...)", "adaptation/predict.py", "CAE sentence keep set"],
            ["score_content_relevancy(...)", "knowledge/base.py", "TF-IDF vs published"],
        ],
    )

    h(doc, "5.4 Core Classes (selected)", 2)
    table(
        doc,
        ["Class", "Responsibilities"],
        [
            ["AdminModule", "Capability-gated ETL: ingest, clean, persist, pipeline, reports"],
            ["JournalistModule", "Tools + content/evidence CRUD with journalist author_id"],
            ["ContentService", "Validated create/list/update for content domain"],
            ["IngestionService", "CSV discovery, hashing, chunked pandas read, normalize_row"],
            ["CleaningOrchestrator", "Run pipeline; optional write processed snapshots"],
            ["PersistenceService", "Write raw_ingest and kept content bundles"],
            ["EditorService", "Queues, urgency, approve/reject/rework/assign"],
            ["ManagerService", "Analytics + delegates review to EditorService"],
            ["PublisherService", "Publication row lifecycle + templates"],
            ["AIAService", "Heuristics + story pitches + performance loop"],
            ["AdaptationService / ReviewService", "Create drafts; approve/reject/regen/final"],
            ["UserService", "Create users with employee+desk profile; reset password"],
            ["BaseDAO and *DAO", "Table SQL CRUD"],
            ["Content / User / ... entities", "Dataclass payloads for inserts"],
        ],
    )

    h(doc, "5.5 Import Dependency Example — Login", 2)
    code(
        doc,
        "api.routers.auth.login\n"
        "  → modules.authentication.auth_service.authenticate\n"
        "      → dao.user_dao.UserDAO.read_by_username\n"
        "      → security.verify_password\n"
        "      → security.create_access_token (JWT HS256)\n"
        "      → _save_cli_token (optional CLI file)\n"
        "      → _user_payload → permission_service.capabilities_for_role\n"
        "                      → UserRepository.get_profile_ids\n"
        "  → api.schemas.auth.LoginResponse (session_token = JWT)",
    )
    p(
        doc,
        "If verify_password were removed, any password would fail closed (or worse if bypassed). "
        "If capabilities_for_role were wrong, users could reach wrong desks despite valid login.",
    )
    doc.add_page_break()
