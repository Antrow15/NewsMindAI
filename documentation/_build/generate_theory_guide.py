"""Full-project theoretical concepts guide for NewsMindAI V2 (no source dumps)."""

from __future__ import annotations

import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
DOC_ROOT = BUILD.parent
OUT_DOCX = DOC_ROOT / "NewsMind_Theoretical_Concepts_Guide.docx"
OUT_PDF = DOC_ROOT / "NewsMind_Theoretical_Concepts_Guide.pdf"

sys.path.insert(0, str(BUILD))
import docx_helpers as H  # noqa: E402


def concept(doc, title: str, meaning: str, why: str, where: str, files: str, related: str = ""):
    H.h(doc, title, 3)
    H.table(
        doc,
        ["Aspect", "Explanation"],
        [
            ["What it is", meaning],
            ["Why it exists", why],
            ["How NewsMind uses it", where],
            ["Primary files / folders", files],
            *([("Related concepts", related)] if related else []),
        ],
    )


def build() -> Path:
    doc = H.setup_document()

    # Cover
    for _ in range(2):
        doc.add_paragraph()
    t = doc.add_paragraph()
    t.alignment = 1
    r = t.add_run("NewsMind AI V2")
    H.set_run_font(r, size=28, bold=True, color=H.NAVY)
    s = doc.add_paragraph()
    s.alignment = 1
    r = s.add_run("Complete Theoretical Concepts Guide")
    H.set_run_font(r, size=18, bold=True, color=H.ACCENT)
    n = doc.add_paragraph()
    n.alignment = 1
    r = n.add_run(
        "Every major concept in this project explained theoretically,\n"
        "with where it appears and which files own it.\n"
        "No source-code dumps — concepts and ownership only."
    )
    H.set_run_font(r, size=11, italic=True, color=H.MUTED)
    doc.add_page_break()

    H.h(doc, "0. How to read this document", 1)
    H.p(
        doc,
        "This is a concept encyclopedia for the entire NewsMindAI V2 application. For each idea "
        "you get: meaning, purpose, how the project applies it, and the files responsible. "
        "Open those files in your IDE when you want implementation detail.",
    )
    H.bullet(doc, "Ch 1 — Product & architecture")
    H.bullet(doc, "Ch 2 — Languages, frameworks, libraries")
    H.bullet(doc, "Ch 3 — Configuration & environment")
    H.bullet(doc, "Ch 4 — Security, JWT, passwords, RBAC")
    H.bullet(doc, "Ch 5 — HTTP API, schemas, errors, clients")
    H.bullet(doc, "Ch 6 — Roles & desk workflows")
    H.bullet(doc, "Ch 7 — Domain data & database")
    H.bullet(doc, "Ch 8 — Persistence patterns (Entity, DAO, Repository)")
    H.bullet(doc, "Ch 9 — ETL & cleaners")
    H.bullet(doc, "Ch 10 — Machine learning & scoring models")
    H.bullet(doc, "Ch 11 — Console CLI")
    H.bullet(doc, "Ch 12 — Testing, logging, operations")
    H.bullet(doc, "Ch 13 — Master concept → file index")
    doc.add_page_break()

    # 1
    H.h(doc, "1. Product and Architecture Concepts", 1)
    concept(
        doc,
        "1.1 Digital newsroom backend",
        "A system that models editorial work: create stories, attach evidence, review, adapt for channels, publish, and analyze audience signals.",
        "Newsrooms need shared data and role-separated tools instead of disconnected spreadsheets and chats.",
        "V2 exposes the same desks via FastAPI (/docs, /easy) and a console (app.py).",
        "README.md, app.py, api/main.py, modules/*, services/*",
        "RBAC, content lifecycle, publication",
    )
    concept(
        doc,
        "1.2 Modular monolith",
        "One deployable application with internal modules that look like layers, not separate microservices.",
        "Simpler deploy and shared database for a learning/demo newsroom; avoids distributed complexity.",
        "All desks share one Postgres and one Python process (API or CLI).",
        "Entire project root; api/, modules/, services/, dao/, ml/",
        "Layered architecture",
    )
    concept(
        doc,
        "1.3 Layered architecture",
        "Organizing code so presentation, business rules, and persistence stay separated.",
        "Changes in UI/API should not force SQL rewrites; security and tests stay clearer.",
        "HTTP/CLI → modules/services → repository/DAO → DB; cleaners/ml are specialized helpers.",
        "api/, app.py, modules/, services/, repository/, dao/, entities/, cleaners/, ml/, database/",
    )
    concept(
        doc,
        "1.4 Dual interface (API + CLI)",
        "Two entry surfaces sharing business modules.",
        "Operators can use menus; integrators/Swagger/easy UI use HTTP.",
        "CLI calls modules directly; API wraps the same ideas behind routers and schemas.",
        "app.py vs api/main.py + api/routers/*",
    )
    concept(
        doc,
        "1.5 Façade module",
        "A thin orchestration class that checks permission then calls services.",
        "Keeps routers/CLI free of capability + workflow wiring duplication.",
        "AdminModule and JournalistModule are primary façades.",
        "modules/admin/admin_module.py, modules/journalist/journalist_module.py, modules/content/content_module.py",
        "Capability RBAC",
    )
    doc.add_page_break()

    # 2
    H.h(doc, "2. Languages, Frameworks, and Libraries", 1)
    concept(doc, "2.1 Python", "Primary language of the backend.", "Rich data/ML ecosystem and fast prototyping.", "Almost all application logic is Python 3.", "All *.py under project root")
    concept(doc, "2.2 FastAPI", "Modern Python web framework generating OpenAPI docs automatically.", "Typed routes, validation, Swagger for desk demos.", "Hosts all HTTP endpoints and /docs.", "api/main.py, api/routers/*, uvicorn run command")
    concept(doc, "2.3 Uvicorn", "ASGI server that runs FastAPI.", "Needed to serve async-capable ASGI apps.", "python -m uvicorn api.main:app --reload", "README.md, requirements.txt")
    concept(doc, "2.4 Pydantic", "Data validation using Python type hints.", "Rejects bad HTTP bodies early with clear field errors.", "api/schemas/* define request/response contracts.", "api/schemas/, api/main.py validation handler")
    concept(doc, "2.5 PostgreSQL + psycopg2", "Relational database and its Python driver.", "Structured newsroom data with FKs and SQL reporting.", "All durable desk/ETL/ML-train data lives in Postgres.", "database/connection.py, database/newsmind.sql, dao/*")
    concept(doc, "2.6 pandas", "Tabular data library.", "Chunked CSV reading for ingest and ML dataset push.", "services/ingestion_service.py, ml/training/*", "CSV ETL")
    concept(doc, "2.7 scikit-learn / joblib / XGBoost", "Classical ML stack: pipelines, serialization, gradient boosting.", "Train urgency/CAE offline; load artifacts online.", "ml/training/*, ml/editor/*, ml/adaptation/*, artifacts/models/", "Trained models chapter")
    concept(doc, "2.8 PyJWT", "Library to create/verify JSON Web Tokens.", "Signed access tokens for API auth.", "modules/authentication/security.py", "Chapter 4 JWT")
    concept(doc, "2.9 spaCy (optional)", "NLP toolkit; here used lightly for entities with fallback.", "Entity hints without hard dependency on heavy models.", "ml/common/entities.py", "Regex fallback if spaCy path unavailable")
    concept(doc, "2.10 pytest + httpx/TestClient", "Automated testing of API and pipeline pieces.", "Regression safety for desks and auth.", "tests/*", "Chapter 12")
    doc.add_page_break()

    # 3
    H.h(doc, "3. Configuration and Environment Concepts", 1)
    concept(doc, "3.1 .env configuration", "Key=value settings outside code.", "Secrets and machine-specific values should not be hardcoded.", "Loaded into os.environ once; DB and JWT settings come from here.", "config/env_loader.py, .env, ENV.example")
    concept(doc, "3.2 DatabaseConfig", "Immutable object holding DB connect parameters.", "Centralizes DSN options including SSL and keepalives.", "Used whenever a connection opens.", "config/db_config.py, database/connection.py")
    concept(doc, "3.3 Runtime pipeline settings", "Tunables for CSV chunk size, insert batch, file-by-file pipeline, processed snapshots.", "Large CSV ingest needs memory/throughput control.", "Read via config/runtime.py helpers during ingest/pipeline.", "config/runtime.py, NEWSROOM_* env vars")
    concept(doc, "3.4 Application constants", "Stable enums and maps: roles, capabilities, platforms, password policy, TTL.", "Single source of truth for business vocabulary.", "Imported across API, services, cleaners, auth.", "config/constants.py")
    concept(doc, "3.5 Required JWT secret", "Signing key must come from environment.", "Prevents forged tokens; no silent insecure default in code.", "get_jwt_secret() fails clearly if NEWSROOM_JWT_SECRET missing.", "config/constants.py, ENV.example")
    doc.add_page_break()

    # 4
    H.h(doc, "4. Security, Authentication, Authorization", 1)

    H.h(doc, "4.1 Authentication vs authorization", 2)
    H.p(doc, "Authentication answers “who are you?” Authorization answers “what may you do?” NewsMind authenticates with password + JWT, then authorizes with role capabilities.")

    concept(
        doc,
        "4.2 JWT (JSON Web Token)",
        "A three-part signed string: header.payload.signature. Payload holds claims; signature proves integrity using a secret (HS256).",
        "Lets the API accept a Bearer token and verify it cryptographically without an opaque session-id table.",
        "Login returns JWT as session_token; every protected route verifies it, then reloads the user from DB. Logout revokes the token’s jti in-process.",
        "security.py (create/decode), auth_service.py (login/resolve/logout), api/deps.py, api/routers/auth.py, api/schemas/auth.py, constants.get_jwt_secret",
        "Bearer auth, jti denylist, PBKDF2",
    )
    concept(
        doc,
        "4.3 HS256",
        "HMAC-SHA256 symmetric signing algorithm for JWTs.",
        "Simple shared-secret model suitable for a single backend.",
        "JWT_ALGORITHM = HS256; secret from NEWSROOM_JWT_SECRET.",
        "config/constants.py, modules/authentication/security.py",
    )
    concept(
        doc,
        "4.4 JWT claims used here",
        "Named fields inside the payload: sub/user_id, username, role_code, iat, exp, jti, type.",
        "Identify the user, expire the token, and support logout revocation.",
        "Created at login; checked on resolve_session.",
        "modules/authentication/security.py, auth_service.py",
    )
    concept(
        doc,
        "4.5 jti denylist (logout)",
        "A server-side set of revoked token IDs until their natural expiry.",
        "JWTs are otherwise valid until exp; logout needs an explicit revoke mechanism.",
        "_REVOKED_JTI in auth_service; process-local (cleared on process restart).",
        "modules/authentication/auth_service.py",
    )
    concept(
        doc,
        "4.6 Bearer authentication",
        "HTTP pattern: Authorization: Bearer <token>.",
        "Standard for SPA/API clients including Swagger Authorize and /easy.",
        "HTTPBearer dependency extracts the string for verification.",
        "api/deps.py, api/static/easy.html, Swagger /docs",
    )
    concept(
        doc,
        "4.7 PBKDF2 password hashing",
        "Slow hashing of passwords with salt so stolen DB hashes are hard to crack.",
        "Never store plaintext passwords; ERD has one password_hash column.",
        "Stored as salt_hex$digest_hex; verified with constant-time compare.",
        "modules/authentication/security.py; users.password_hash column",
    )
    concept(
        doc,
        "4.8 Strong password policy",
        "Rules for minimum length and character classes.",
        "Reduce weak passwords on change/reset.",
        "Enforced via validators / StrongPasswordStr on change and admin reset.",
        "utils/validators.py, api/schemas/rules.py, api/schemas/auth.py",
    )
    concept(
        doc,
        "4.9 RBAC (Role-Based Access Control)",
        "Permissions granted by role rather than per-user ACL lists.",
        "Newsroom desks map cleanly to roles.",
        "users.role_id → role.role_code → ROLE_CAPABILITIES tuple of capability strings.",
        "config/constants.py, services/permission_service.py, database role/users tables",
    )
    concept(
        doc,
        "4.10 Capability",
        "A fine-grained action key such as publish, adapt, pitch_review, journalist_tools.",
        "More precise than checking role names in every endpoint.",
        "require_capability_session(capability, token) after JWT resolve.",
        "services/access.py, services/permission_service.py, routers under api/routers/",
    )
    concept(
        doc,
        "4.11 Desk profile",
        "1:1 extension row off users for a specialty desk (journalist_id, editor_id, …).",
        "Content authorship and desk metadata are not the same as login identity.",
        "Created at user seed/onboarding; journalist author_id uses journalist_id.",
        "entities/* desk files, dao/* desk DAOs, repository/user_repository.py",
    )
    concept(
        doc,
        "4.12 CLI session file",
        "Optional local JSON holding the last JWT for console menus.",
        "Console has no Authorization header; needs a place to remember login.",
        "logs/.session_token written on login; cleared on logout.",
        "modules/authentication/auth_service.py, app.py",
    )
    doc.add_page_break()

    # 5
    H.h(doc, "5. HTTP API, Schemas, Errors, Clients", 1)
    concept(doc, "5.1 REST-style HTTP API", "Resources manipulated with GET/POST/PUT and JSON bodies.", "Language-agnostic integration and Swagger try-outs.", "Prefixes: /auth, /journalist, /aia, /cae, /publisher, /editor, /manager, /admin.", "api/routers/*.py")
    concept(doc, "5.2 OpenAPI / Swagger", "Machine-readable API contract + interactive UI.", "Learn and test endpoints without a separate frontend build.", "/docs served by FastAPI; tags order desks pedagogically.", "api/main.py")
    concept(doc, "5.3 Dependency injection (Depends)", "Framework supplies shared inputs (token, user) into handlers.", "Avoid repeating auth parsing in every route.", "get_session_token / get_current_user.", "api/deps.py")
    concept(doc, "5.4 Request/response schema models", "Typed contracts for bodies and responses.", "Validate early; document fields in OpenAPI.", "Per-desk modules under api/schemas/; shared rules in rules.py.", "api/schemas/*")
    concept(doc, "5.5 CORS", "Browser cross-origin policy configuration.", "Allow local HTML/tools to call the API during demos.", "CORSMiddleware allow_origins=['*'] in create_app (tighten for production).", "api/main.py")
    concept(doc, "5.6 Exception → HTTP mapping", "Convert domain errors into status codes and JSON detail.", "Clients need consistent 401/403/404/400/422/503/500 behavior.", "handlers in main.py + raise_http_error helper.", "api/main.py, api/http_errors.py, utils/errors.py")
    concept(doc, "5.7 easy.html tester UI", "Single-page HTML/JS client for role endpoints.", "Easier manual testing than Swagger for multi-step desk flows.", "Stores JWT in localStorage; GROUPS map forms to paths.", "api/static/easy.html, GET /easy")
    concept(doc, "5.8 HTTP status semantics used", "401 unauthenticated, 403 forbidden, 404 missing, 400 business validation, 422 schema validation, 503 missing model/file, 500 unexpected.", "Clients and tests assert these meanings.", "Across routers and http_errors.", "tests/*, api/http_errors.py")
    doc.add_page_break()

    # 6
    H.h(doc, "6. Roles and Desk Workflow Concepts", 1)
    concept(doc, "6.1 Administrator", "Full capability set including pipeline and user management.", "Bootstrap data and manage accounts.", "Admin router + console ML/pipeline menus.", "api/routers/admin.py, modules/admin/, services/user/, ml/training via console")
    concept(doc, "6.2 Journalist desk", "Create news/articles with mandatory evidence; AI assist tools; submit status.", "Reporters produce verifiable draft content.", "JournalistModule + content service + journalist ML helpers.", "modules/journalist/, services/content/, services/journalist/*, api/routers/journalist.py")
    concept(doc, "6.3 Evidence", "Supporting documents/text linked to a content item.", "Credibility and editorial trust require attachments.", "Created with news/article or added later; used in credibility.", "entities/content/evidence.py, evidence_dao, journalist endpoints")
    concept(doc, "6.4 Content validation & relevancy tools", "Check fields and see related published stories.", "Reduce duplicates and weak drafts before submit.", "validate + related-content use validators + TF-IDF over published corpus.", "services/journalist/content_validate.py, ml/knowledge/base.py")
    concept(doc, "6.5 Duplicate detection", "Find near-duplicate documents via similarity.", "Avoid publishing the same story twice.", "Journalist duplicates tool; editor pitch duplicates.", "services/journalist/duplicate_check.py, ml/common/similarity.py, editor_service")
    concept(doc, "6.6 Credibility assessment", "Split claims and rank against attached evidence.", "Quick evidence-backed sanity check.", "Requires content body + evidence list.", "services/journalist/credibility.py, evidence_search.py")
    concept(doc, "6.7 Audience Insight Analyst (AIA)", "Scores engagement/interest/trend; generates story pitches; performance loop.", "Decide what to cover next using signals.", "Heuristic scores + story_pitch persistence.", "ml/aia/, services/aia/, api/routers/aia.py")
    concept(doc, "6.8 Story pitch", "Proposed story idea with priority and scores.", "Bridge from analytics to editorial assignment.", "Statuses like submitted/approved/rejected; editors review.", "story_pitch table/entity/DAO; AIA + editor/manager routers")
    concept(doc, "6.9 Editor desk", "Review pitches/content; urgency ordering; assign journalists; rework.", "Human quality gate before publishing.", "EditorService + urgency model + API.", "services/editor/, ml/editor/, api/routers/editor.py")
    concept(doc, "6.10 Rework status", "Send content back to journalist for changes.", "Soft reject that keeps the item alive.", "Editor content rework action.", "editor_service, content status constants")
    concept(doc, "6.11 Newsroom manager", "Same review powers plus operational analytics (bottlenecks, workload, deadline risk, resources).", "Oversee the whole desk pipeline.", "ManagerService delegates review to EditorService and adds SQL aggregates.", "services/manager/, api/routers/manager.py")
    concept(doc, "6.12 Content Adaptation Editor (CAE)", "Create platform-specific adapted drafts and human-review them.", "One article must fit social/print/web/newsletter constraints.", "AdaptationService + ReviewService + CAE ML.", "services/adaptation/, ml/adaptation/, api/routers/cae.py, adaptation_* tables")
    concept(doc, "6.13 Publisher desk", "Approve for publication, assign template, preview, publish or schedule, analytics.", "Controlled release of approved content.", "Publication row lifecycle tied to content.", "services/publisher/, publication_dao, api/routers/publisher.py")
    concept(doc, "6.14 Content lifecycle", "draft → submitted → approved|rejected|rework → published.", "Shared state machine across desks.", "Enforced by validators and desk services.", "config/constants.py ALLOWED_CONTENT_STATUSES, content services")
    concept(doc, "6.15 Publication templates", "Named layout/channel presets (web, print, social, newsletter).", "Standardize output packaging.", "Constants list; assigned on publication row.", "config/constants.py PUBLICATION_TEMPLATES, publisher_service")
    doc.add_page_break()

    # 7
    H.h(doc, "7. Domain Data and Database Concepts", 1)
    concept(doc, "7.1 Relational modeling", "Data in tables with keys and relationships.", "Integrity for users, content, evidence, publication.", "Defined in newsmind.sql; accessed via SQL DAOs.", "database/newsmind.sql")
    concept(doc, "7.2 Primary key / foreign key", "PK uniquely identifies a row; FK references another table.", "Prevent orphan content and enforce authorship links.", "Throughout schema (users→role, content→journalist, evidence→content, …).", "database/newsmind.sql")
    concept(doc, "7.3 Destructive schema bootstrap", "init-db drops public schema and recreates from SQL.", "Guarantees a clean teaching database.", "python app.py --init-db → apply SQL + seed demo users.", "database/connection.py init_schema, newsmind.sql, seed_demo_users.py")
    concept(doc, "7.4 Demo user seeding", "Create seven role accounts with known local passwords.", "Immediate login for every desk after init.", "Employees + users + desk profiles.", "database/seed_demo_users.py, DEMO_PASSWORDS in constants")
    concept(doc, "7.5 Optional temp seed SQL", "Extra metro/probe desk data for demos.", "Richer queues without manual typing.", "Applied manually after init-db.", "database/seed_temp_data.sql")
    concept(doc, "7.6 Content specialization (news vs article)", "Shared content row plus child table for type-specific fields.", "Avoid null-heavy single table while sharing workflow status.", "content_kind drives which child is written.", "entities/content/*, content_repository, news_dao, article_dao")
    concept(doc, "7.7 Staging tables (raw_ingest, ingest_file)", "Temporary/operational tables for ETL.", "Trace what was imported and skip unchanged files via hash.", "Ingest writes pending/rejected/kept markers; ingest_file stores hashes.", "dao/raw_ingest_dao.py, dao/ingest_file_dao.py")
    concept(doc, "7.8 ML training tables", "ml_train_urgency / ml_train_adaptation hold cleaned training rows.", "Separate training corpora from live desk content.", "Push from dataset CSVs then train to artifacts.", "schema ml_train_*; ml/training/*")
    concept(doc, "7.9 Indexes", "Structures speeding common filters (status, hashes).", "Queue and ETL queries stay responsive.", "Declared in newsmind.sql.", "database/newsmind.sql")
    concept(doc, "7.10 Connection-per-call lifecycle", "Open cursor/connection for an operation, commit, close.", "Simple and safe without a pool for this app size.", "db_cursor context manager.", "database/connection.py, dao/base_dao.py")
    concept(doc, "7.11 RealDictCursor", "DB rows returned as dictionary-like objects.", "Convenient field access in services without ORM.", "Used inside db_cursor.", "database/connection.py")
    doc.add_page_break()

    # 8
    H.h(doc, "8. Persistence Design Patterns", 1)
    concept(doc, "8.1 Entity (dataclass)", "In-memory representation of a table row.", "Type fields before SQL insert.", "entities/ tree mirrors major tables.", "entities/**/*.py")
    concept(doc, "8.2 DAO (Data Access Object)", "Class encapsulating SQL for one table.", "Keep SQL out of routers/services.", "BaseDAO helpers + specialized DAOs.", "dao/base_dao.py, dao/*.py")
    concept(doc, "8.3 Repository", "Coordinates multiple DAOs for one use case.", "Saving content+news/article together is one business action.", "ContentRepository, UserRepository; NewsroomRepository compatibility façade.", "repository/*.py")
    concept(doc, "8.4 Service layer", "Business rules, orchestration, ML calls, validation.", "Single place for desk logic reused by API and CLI.", "services/**", "services/*")
    concept(doc, "8.5 Dependency injection into façades", "Optional service instances passed into module constructors.", "Testing and substitution without rewriting façades.", "AdminModule / JournalistModule __init__.", "modules/admin, modules/journalist")
    doc.add_page_break()

    # 9
    H.h(doc, "9. ETL and Cleaning Concepts", 1)
    concept(doc, "9.1 ETL", "Extract–Transform–Load: pull files, clean, store.", "Bring external CSV corpora into the desk model.", "Admin ingest → clean → persist (or combined pipeline).", "modules/admin/admin_module.py, services/ingestion_service.py, cleaners/, persistence_service.py")
    concept(doc, "9.2 Content-hash skip", "Fingerprint files (MD5 here) to detect new/changed CSVs.", "Avoid re-ingesting unchanged data.", "ingest_file table stores hashes; only_new flag uses them.", "ingestion_service.py, ingest_file_dao.py")
    concept(doc, "9.3 Chunked CSV reading", "Read large files in row batches.", "Control memory on big datasets.", "pandas chunksize from runtime settings.", "ingestion_service.py, config/runtime.py")
    concept(doc, "9.4 Column alias normalization", "Map varied CSV headers to canonical field names.", "Real datasets disagree on column titles.", "utils/csv_fields.normalize_row", "utils/csv_fields.py")
    concept(doc, "9.5 Cleaning pipeline / stages", "Ordered transforms each producing kept/rejected sets.", "Quality before DB write; measurable rejects.", "Text → Null → Duplicate → Schema by default.", "cleaners/pipeline.py, cleaners/stages/*, orchestrator.py")
    concept(doc, "9.6 Quality / cleaning report", "Structured stats about a clean run.", "Audit what was dropped and why.", "Persisted via ReportService to cleaning_report.", "cleaners/quality_report.py, services/report_service.py")
    concept(doc, "9.7 File-by-file pipeline mode", "Process each CSV through ingest-clean-persist separately.", "Failure isolation and clearer progress on many files.", "Controlled by NEWSROOM_PIPELINE_FILE_BY_FILE.", "admin_module.run_pipeline, config/runtime.py")
    doc.add_page_break()

    # 10
    H.h(doc, "10. Machine Learning and Scoring Concepts", 1)
    H.p(
        doc,
        "Important distinction: some features are trained models (artifacts on disk); some are "
        "heuristics/formulas; some are classical similarity search. All are “intelligence helpers,” "
        "but operations differ.",
    )

    concept(
        doc,
        "10.1 Supervised learning (general)",
        "Learn a mapping from labeled examples (X → y).",
        "Urgency classes and sentence keep/drop labels come from datasets.",
        "Training jobs write joblib artifacts consumed at inference.",
        "ml/training/*, ml/editor/*, ml/adaptation/training.py",
    )
    concept(
        doc,
        "10.2 TF-IDF",
        "Represents text by term importance (frequent in doc, rare in corpus).",
        "Lightweight numeric features for classification and similarity without deep learning.",
        "Used in urgency features, CAE features, and relevancy/duplicates ranking.",
        "ml/common/similarity.py, ml/editor/*, ml/adaptation/features.py",
    )
    concept(
        doc,
        "10.3 Cosine similarity",
        "Angle-based similarity between vectors (1 = same direction).",
        "Rank related documents and near-duplicates.",
        "rank() and similar_pairs() utilities.",
        "ml/common/similarity.py",
    )
    concept(
        doc,
        "10.4 Editor queue urgency model (trained)",
        "Classifier mapping headline/body → urgency for review ordering.",
        "Editors need prioritization beyond FIFO.",
        "XGBoost multiclass → desk levels urgent/high/medium/low; artifact under editor_queue_urgency/.",
        "ml/editor/queue_urgency.py; used by services/editor/editor_service.py; trained via ml/training",
        "Fallback if artifact missing",
    )
    concept(
        doc,
        "10.5 CAE sentence-retention model (trained)",
        "For each sentence, predict whether to keep it for a target platform; then format output.",
        "Channel limits differ (social short vs web longer) without calling an external LLM.",
        "Logistic regression pipeline + platform thresholds/limits; human review afterward.",
        "ml/adaptation/*; services/adaptation/*; api/routers/cae.py; artifacts/models/cae/",
        "Extractive adaptation",
    )
    concept(
        doc,
        "10.6 Extractive vs generative adaptation",
        "Extractive selects from existing sentences; generative would invent new wording.",
        "Deterministic, trainable offline, no paid LLM dependency.",
        "CAE path is extractive with optional regenerate guided by remarks.",
        "ml/adaptation/predict.py, platforms.py, review_service.py",
    )
    concept(
        doc,
        "10.7 AIA heuristic scoring",
        "Formulas on views/likes/shares/comments and keyword cues for trends.",
        "Useful analytics without requiring a telemetry-trained model yet.",
        "predict_engagement / interest / trend; no model.joblib.",
        "ml/aia/audience_scores.py, services/aia/aia_service.py",
        "No category prediction endpoint",
    )
    concept(
        doc,
        "10.8 Published-content relevancy corpus",
        "Similarity search against live published desk content only.",
        "Avoid polluting recommendations with seed/history CSV noise (project design).",
        "load_published_documents + score_content_relevancy.",
        "ml/knowledge/base.py",
    )
    concept(
        doc,
        "10.9 Model artifact",
        "Serialized fitted estimator and supporting objects (vectorizers, labels, thresholds).",
        "Inference must match training feature pipeline.",
        "Stored under artifacts/models/… as joblib (+ metadata JSON for CAE).",
        "artifacts/models/editor_queue_urgency/, artifacts/models/cae/",
    )
    concept(
        doc,
        "10.10 Training vs inference",
        "Training fits offline; inference predicts online per request/console action.",
        "Keeps API latency manageable and datasets curated.",
        "Push/train via ml.training or admin console; predict inside desk services.",
        "ml/training/console.py, ingest_clean.py",
    )
    concept(
        doc,
        "10.11 Fallback behavior",
        "When a trained artifact is missing, return a conservative default or service error mapped to 503.",
        "Desk should degrade predictably.",
        "Urgency has fallback source; CAE may surface ValidationError → 503 path.",
        "ml/editor/queue_urgency.py, api/http_errors.py",
    )
    concept(
        doc,
        "10.12 Entity extraction helper",
        "Pull people/org/place-like spans from text.",
        "Support journalist tooling / enrichment.",
        "spaCy ruler or regex fallback in common entities module.",
        "ml/common/entities.py",
    )
    doc.add_page_break()

    # 11
    H.h(doc, "11. Console CLI Concepts", 1)
    concept(doc, "11.1 Interactive role menu", "Text UI that shows only actions the logged-in role can perform.", "Operate pipeline and desks without HTTP.", "Built from capabilities after resolve_session().", "app.py, utils/console_ui.py")
    concept(doc, "11.2 Argparse commands", "Flags like --init-db, --ingest, --pipeline for scripting.", "Automate ops in shells/CI.", "main() dispatch in app.py.", "app.py")
    concept(doc, "11.3 Console UX helpers", "Prompts, headers, pretty printers, cancel handling.", "Make CLI usable for demos.", "utils/console_ui.py, utils/progress.py", "utils/*")
    doc.add_page_break()

    # 12
    H.h(doc, "12. Testing, Logging, Operations", 1)
    concept(doc, "12.1 Automated API tests", "Call FastAPI via TestClient with demo logins.", "Catch auth/validation/desk regressions.", "tests/test_api_*.py", "tests/")
    concept(doc, "12.2 Pipeline integration tests", "Exercise cleaners/persistence/ingest paths.", "ETL is easy to break with schema changes.", "tests/test_integration_pipeline.py, test_single_file_ingest.py", "tests/")
    concept(doc, "12.3 db_ready fixture", "Skip DB tests when Postgres/schema unavailable.", "Developers without DB still run what they can.", "tests/conftest.py", "tests/conftest.py")
    concept(doc, "12.4 Logging", "Timestamped diagnostic messages to console/files.", "Debug ingest and unexpected API errors.", "utils/logger.py; logs/ directory", "utils/logger.py, api/main.py exception logging")
    concept(doc, "12.5 Progress messages", "Human-readable pipeline step output.", "Long CSV jobs need feedback.", "utils/progress.py used by ingest/admin", "utils/progress.py")
    concept(doc, "12.6 Application error hierarchy", "Typed errors with user-facing messages.", "Map cleanly to HTTP and CLI error printers.", "AppError, ValidationError, NotFoundError, AuthError, PermissionDeniedError.", "utils/errors.py")
    doc.add_page_break()

    # 13 master index
    H.h(doc, "13. Master Concept → File Index", 1)
    H.p(doc, "Use this as a lookup table for the whole project.")
    H.table(
        doc,
        ["Concept cluster", "Go read (ownership)"],
        [
            ["App entry / wiring", "api/main.py, app.py, README.md"],
            ["Env & constants", "config/env_loader.py, db_config.py, runtime.py, constants.py"],
            ["JWT & passwords", "modules/authentication/security.py, auth_service.py"],
            ["HTTP auth deps", "api/deps.py, api/routers/auth.py, api/schemas/auth.py"],
            ["RBAC", "constants ROLE_CAPABILITIES, permission_service.py, access.py"],
            ["Journalist desk", "modules/journalist/, services/journalist/*, services/content/, routers/journalist.py"],
            ["AIA desk", "ml/aia/, services/aia/, routers/aia.py"],
            ["Editor desk", "ml/editor/, services/editor/, routers/editor.py"],
            ["Manager desk", "services/manager/, routers/manager.py"],
            ["CAE desk", "ml/adaptation/, services/adaptation/, routers/cae.py"],
            ["Publisher desk", "services/publisher/, publication DAO, routers/publisher.py"],
            ["Admin ETL", "modules/admin/, ingestion_service, cleaners/, persistence_service, routers/admin.py"],
            ["Users/categories admin", "services/user/, content_service.add_category"],
            ["DB schema & seeds", "database/newsmind.sql, connection.py, seed_demo_users.py, seed_temp_data.sql"],
            ["Entities/DAOs/Repos", "entities/, dao/, repository/"],
            ["ML training", "ml/training/, ml/*/dataset/, artifacts/models/"],
            ["Similarity/relevancy", "ml/common/, ml/knowledge/"],
            ["Validation", "utils/validators.py, api/schemas/rules.py"],
            ["Errors/HTTP map", "utils/errors.py, api/http_errors.py"],
            ["Frontend tester", "api/static/easy.html"],
            ["Tests", "tests/*"],
            ["Logging/progress/CLI UI", "utils/logger.py, progress.py, console_ui.py, helpers.py, csv_fields.py"],
        ],
    )

    H.h(doc, "14. What this project deliberately does / does not do", 1)
    H.h(doc, "Implemented (conceptually present)", 2)
    H.bullet(doc, "JWT access tokens + password hashing + capability RBAC")
    H.bullet(doc, "Full desk APIs and console parity for pipeline/core ops")
    H.bullet(doc, "ETL cleaners and persistence into relational desk model")
    H.bullet(doc, "Trained urgency + CAE models; heuristic AIA; TF-IDF relevancy")
    H.bullet(doc, "Publication workflow and adaptation review workflow")
    H.h(doc, "Not the focus / not present", 2)
    H.bullet(doc, "No microservices mesh, no message broker")
    H.bullet(doc, "No ORM (SQLAlchemy); raw SQL DAOs instead")
    H.bullet(doc, "No user_session table; JWT + jti denylist instead")
    H.bullet(doc, "No generative LLM rewrite API; CAE is extractive")
    H.bullet(doc, "No trained category-prediction API endpoint")
    H.bullet(doc, "No React SPA; /easy HTML + Swagger are the UIs")

    H.h(doc, "Closing", 1)
    H.p(
        doc,
        "Every major idea in NewsMindAI V2—product shape, layers, libraries, config, security/JWT, "
        "API machinery, each desk, database modeling, persistence patterns, ETL, ML/scoring, CLI, "
        "and testing—has a theoretical explanation here and a file ownership pointer. Study by "
        "concept first; open the listed files second.",
    )

    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    doc.save(OUT_DOCX)
    return OUT_DOCX


def main() -> int:
    print("Building full theoretical concepts DOCX...")
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
