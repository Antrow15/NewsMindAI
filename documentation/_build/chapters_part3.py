"""Chapters 12–18 + appendices of the NewsMind V2 learning guide."""

from __future__ import annotations

from docx_helpers import bullet, code, h, note, numbered, p, table


def chapter_12(doc):
    h(doc, "12. External Libraries and Integrations", 1)
    table(
        doc,
        ["Library", "Why used", "Where", "Replace impact"],
        [
            ["fastapi", "HTTP API + OpenAPI", "api/*", "Rewrite routers"],
            ["uvicorn", "ASGI server", "run command", "Any ASGI server"],
            ["PyJWT", "JWT create/verify (HS256)", "modules/authentication/security.py", "python-jose / Authlib"],
            ["pydantic", "Schemas", "api/schemas", "Manual validation"],
            ["psycopg2-binary", "Postgres driver", "database/, dao/", "asyncpg/SQLAlchemy"],
            ["pandas", "CSV chunking", "ingestion, ml training", "csv module slower"],
            ["numpy/scipy", "Numeric ML", "ml/*", "Required by sklearn stack"],
            ["scikit-learn", "TF-IDF, LR pipelines", "ml/common, adaptation", "Rewrite features"],
            ["xgboost", "Urgency classifier", "ml/training, editor", "Another classifier"],
            ["joblib", "Model serialize", "artifacts load/save", "pickle/cloudpickle"],
            ["spacy", "Optional NER", "ml/common/entities", "Regex fallback exists"],
            ["httpx", "TestClient transport", "tests", "requests (older)"],
            ["pytest", "Tests", "tests/", "unittest"],
        ],
    )
    p(
        doc,
        "Custom logic vs framework: FastAPI only routes/validation/docs. Business rules, RBAC map, "
        "cleaners, DAO SQL, and ML labeling are project-owned.",
    )
    doc.add_page_break()


def chapter_13(doc):
    h(doc, "13. Testing and Debugging", 1)

    h(doc, "13.1 Framework and Layout", 2)
    bullet(doc, "pytest with tests/conftest.py fixing sys.path so V2 wins over sibling trees.")
    bullet(doc, "db_ready fixture skips tests if Postgres/schema unavailable.")
    bullet(doc, "API tests use fastapi.testclient.TestClient(app) + DEMO_PASSWORDS + logout cleanup.")

    h(doc, "13.2 What Exists", 2)
    table(
        doc,
        ["File", "Coverage"],
        [
            ["test_api_auth_password.py", "Weak password 422; admin reset strength"],
            ["test_api_journalist.py", "Authz, validate, desk CRUD, OpenAPI paths, raw-ingest ownership"],
            ["test_api_aia.py", "AIA endpoints, 403 for journalist, no predict-category"],
            ["test_api_cae_publisher_editor.py", "CAE/editor/publisher/manager flows; skip if no CAE model"],
            ["test_integration_pipeline.py", "Cleaners + persistence; admin ingest_file path"],
            ["test_single_file_ingest.py", "Hash tracking; ingest/clean/report"],
        ],
    )
    note(doc, "Missing areas (do not invent): no frontend unit tests; limited pure unit tests of DAOs in isolation; no load tests.")

    h(doc, "13.3 How to Run", 2)
    code(
        doc,
        "$env:PYTHONPATH = \"G:\\NewsMind AI\\NewsMindAI V2\"\n"
        "pytest -q\n"
        "# or focused:\n"
        "pytest tests/test_api_journalist.py -q",
    )

    h(doc, "13.4 Debugging Approach", 2)
    numbered(doc, "Reproduce with /easy or curl; capture status + detail JSON.")
    numbered(doc, "Check Bearer token present and not expired (API restart clears memory sessions).")
    numbered(doc, "Confirm role capabilities for the endpoint.")
    numbered(doc, "For ML 503: verify artifacts/models/.../model.joblib exists; train if needed.")
    numbered(doc, "For DB errors: app.py --status / --init-db; check .env.")
    numbered(doc, "Read logs/ and console progress lines for ETL.")
    numbered(doc, "Set breakpoints in router → service → DAO along the flow in Chapter 9.")
    doc.add_page_break()


def chapter_14(doc):
    h(doc, "14. Code-Level File-by-File Explanation", 1)
    p(
        doc,
        "This chapter walks the most important source files with real snippets and explanations. "
        "Every file listed in Chapter 3 participates; here we deepen the critical path files.",
    )

    h(doc, "14.1 api/main.py — Application Entry", 2)
    p(doc, "Purpose: construct FastAPI app, wire cross-cutting concerns, export app.")
    code(
        doc,
        "application.include_router(auth_router)\n"
        "application.include_router(journalist_router)\n"
        "...\n"
        "application.include_router(admin_router)\n"
        "app = create_app()",
    )
    bullet(doc, "Imports routers package, auth errors, AppError, load_dotenv.")
    bullet(doc, "CORS allow_origins=['*'] — convenient for local demos; tighten for production.")
    bullet(doc, "Order of exception handlers matters for typed errors vs catch-all Exception.")

    h(doc, "14.2 api/deps.py — Auth Dependencies", 2)
    code(
        doc,
        "bearer_scheme = HTTPBearer(auto_error=False)\n\n"
        "def get_session_token(creds=Depends(bearer_scheme)) -> str:\n"
        "    if creds is None or not creds.credentials:\n"
        "        raise HTTPException(401, detail=\"Login first...\")\n"
        "    return creds.credentials.strip()\n\n"
        "def get_current_user(token: str = Depends(get_session_token)) -> dict:\n"
        "    return resolve_session(token)  # or 401",
    )
    p(doc, "auto_error=False lets the app supply a friendlier 401 message than default Bearer challenge.")

    h(doc, "14.3 modules/authentication/security.py", 2)
    bullet(doc, "hash_password: os.urandom salt → pbkdf2_hmac → salt$digest string.")
    bullet(doc, "verify_password: split hash, recompute, compare_digest.")
    bullet(doc, "create_access_token / decode_access_token: PyJWT HS256 via get_jwt_secret().")
    p(doc, "If iterations lowered drastically, hashes verify faster but weaker against brute force.")

    h(doc, "14.4 modules/authentication/auth_service.py", 2)
    bullet(doc, "authenticate: username lookup, active check, verify, issue JWT, optional CLI file save.")
    bullet(doc, "_user_payload attaches capabilities and desk profile IDs.")
    bullet(doc, "resolve_session verifies JWT, checks jti denylist, reloads user from DB.")
    bullet(doc, "logout revokes jti until token exp; clears CLI file when matching.")
    bullet(doc, "change_password / admin_reset_password enforce require_password.")

    h(doc, "14.5 services/access.py + permission_service.py", 2)
    p(
        doc,
        "access.require_capability_session is the single gate used by modules and many routers. "
        "permission_service maps role→capabilities; admin short-circuits to allow all.",
    )

    h(doc, "14.6 modules/admin/admin_module.py", 2)
    p(
        doc,
        "Constructor injects IngestionService, CleaningOrchestrator, PersistenceService, ReportService. "
        "Each public method calls _cap(CAP_*). ingest stores raw_ingest pending rows. clean produces "
        "stats + cleaning_report. persist writes kept/rejected. run_pipeline respects "
        "pipeline_file_by_file runtime flag.",
    )

    h(doc, "14.7 services/ingestion_service.py", 2)
    bullet(doc, "list_csv_files: rglob *.csv under data/raw.")
    bullet(doc, "resolve_csv: path traversal guard via resolve + relative_to raw root.")
    bullet(doc, "_read_csv: pandas chunksize; normalize_row; keep rows with title.")
    bullet(doc, "file_needs_ingest: MD5 hash vs ingest_file table.")
    bullet(doc, "ingest_pitches: special-case pitches.csv.")

    h(doc, "14.8 cleaners pipeline", 2)
    code(
        doc,
        "Default stage order:\n"
        "TextCleaner → NullCleaner → DuplicateCleaner → SchemaCleaner\n"
        "Each returns CleanerResult(kept_records, rejected_records, report extras)",
    )

    h(doc, "14.9 services/content/content_service.py", 2)
    p(
        doc,
        "add_news/add_article require evidence list; validate via validate_content_record; write "
        "content then child table then evidence. update_content_status uses require_content_status. "
        "list_raw_ingest used by admin only.",
    )

    h(doc, "14.10 modules/journalist/journalist_module.py", 2)
    p(
        doc,
        "_author_id maps users.profiles.journalist_id or JournalistDAO.ensure_for_user — critical "
        "because content.author_id FK points at journalist.journalist_id, not users.user_id. "
        "credibility refuses empty body or missing evidence.",
    )

    h(doc, "14.11 Desk services", 2)
    bullet(doc, "EditorService: SQL + StoryPitchDAO/ContentDAO + predict_editor_queue_urgency sorting.")
    bullet(doc, "ManagerService: wraps EditorService + aggregate analytics queries.")
    bullet(doc, "PublisherService: PublicationDAO.ensure_for_content; publish sets published.")
    bullet(doc, "AIAService: ml.aia heuristics + StoryPitch persistence + performance SQL.")
    bullet(doc, "AdaptationService/ReviewService: AdaptationDAO + ml.adaptation predict/validate.")

    h(doc, "14.12 dao/base_dao.py and repositories", 2)
    code(
        doc,
        "class BaseDAO:\n"
        "    def execute(self, sql, params=None, fetch='none'):\n"
        "        with db_cursor() as cur:\n"
        "            cur.execute(sql, params)\n"
        "            ...",
    )
    p(doc, "ContentRepository.save_content_bundle centralizes article vs news child creation.")

    h(doc, "14.13 database/connection.py", 2)
    bullet(doc, "get_connection(**dsn_kwargs)")
    bullet(doc, "apply_sql_file splits on ';' after stripping -- comments")
    bullet(doc, "require_schema checks critical table names")
    bullet(doc, "init_schema applies newsmind.sql then seed_demo_users")

    h(doc, "14.14 ml key modules", 2)
    bullet(doc, "queue_urgency.py — cached joblib load; fallback dict if missing.")
    bullet(doc, "adaptation/training.py + predict.py — sentence keep model.")
    bullet(doc, "knowledge/base.py — load published docs; rank by TF-IDF.")
    bullet(doc, "aia/audience_scores.py — pure formulas, no artifact.")
    bullet(doc, "training/console.py — CLI entry for push/train.")

    h(doc, "14.15 app.py console", 2)
    p(
        doc,
        "Builds capability-aware menus; _run_admin pretty-prints pipeline dict results; argparse "
        "flags mirror admin pipeline operations; ML training is menu-driven for administrators.",
    )

    h(doc, "14.16 utils/validators.py & errors.py", 2)
    p(
        doc,
        "Shared require_* functions keep CLI, services, and cleaners consistent. AppError.message "
        "is what users see after HTTP mapping.",
    )
    doc.add_page_break()


def chapter_15(doc):
    h(doc, "15. Design Decisions and Trade-offs", 1)

    table(
        doc,
        ["Decision", "Rationale (from code/docs)", "Alternative"],
        [
            ["Modular monolith", "Shared DB + simple deploy for demo/learning", "Microservices per desk"],
            ["Raw SQL DAOs", "Matches explicit ERD; no ORM magic", "SQLAlchemy/SQLModel"],
            ["Capability dict RBAC", "Small static role set", "Permission tables / Oso / Casbin"],
            ["JWT HS256 access tokens", "Stateless verify + DB user reload; required env secret", "Opaque DB sessions / Redis"],
            ["jti denylist on logout", "Keep logout working without session table", "Redis revoke list"],
            ["PBKDF2 stdlib", "Single password_hash column; no bcrypt dep", "argon2/bcrypt"],
            ["CSV ETL + cleaners", "Batch news corpora onboarding", "Live scrapers/queues"],
            ["Extractive CAE", "Deterministic, trainable offline", "LLM rewrite APIs"],
            ["Heuristic AIA scores", "No engagement telemetry pipeline yet", "Trained regressors"],
            ["Published-only relevancy", "Avoid seed/history pollution (README)", "Static KB CSV"],
            ["easy.html not React", "Zero build step; teach API directly", "Full SPA"],
            ["Sync routes in FastAPI", "psycopg2 sync stack", "asyncpg + async def routes"],
            ["Destructive init SQL", "Fresh teaching DB guaranteed", "Alembic migrations"],
        ],
    )
    note(
        doc,
        "Where original developer intent is not documented, the table states technical "
        "interpretation inferred from structure and README—not a confirmed product manifesto.",
    )
    doc.add_page_break()


def chapter_16(doc):
    h(doc, "16. Practical Learning Exercises", 1)

    h(doc, "Exercise A — Add a new API endpoint", 2)
    numbered(doc, "Add Pydantic models in api/schemas/<area>.py")
    numbered(doc, "Add service method in the correct services/* file")
    numbered(doc, "Add router function with Depends(get_session_token) + capability check")
    numbered(doc, "Add OpenAPI summary; restart uvicorn; verify in /docs and /easy GROUPS if needed")
    numbered(doc, "Add a pytest in tests/")

    h(doc, "Exercise B — Add a database field", 2)
    numbered(doc, "ALTER logic: update database/newsmind.sql AND write a safe migration note (init-db wipes).")
    numbered(doc, "Extend entity dataclass + DAO INSERT/SELECT columns.")
    numbered(doc, "Thread through service + schema if exposed via API.")
    numbered(doc, "Update seed if demo data needs the field.")

    h(doc, "Exercise C — New cleaner stage", 2)
    numbered(doc, "Subclass BaseCleaner in cleaners/stages/")
    numbered(doc, "Register in CleaningPipeline default list")
    numbered(doc, "Extend quality report expectations; add test with sample rows")

    h(doc, "Exercise D — Debug a 403", 2)
    numbered(doc, "Login as journalist; call GET /editor/queue")
    numbered(doc, "Observe 403 PermissionDenied — role lacks pitch_review")
    numbered(doc, "Inspect ROLE_CAPABILITIES to confirm")

    h(doc, "Exercise E — Trace publish", 2)
    numbered(doc, "Create article as journalist → submit → editor approve → publisher publish")
    numbered(doc, "SQL-check content.status and publication.published_at")
    numbered(doc, "Call /journalist/related-content and confirm corpus_size increased")

    h(doc, "Exercise F — Retrain urgency", 2)
    numbered(doc, "python -m ml.training --urgency --fast")
    numbered(doc, "POST /editor/queue/score with a breaking-style headline")
    numbered(doc, "Compare confidence/probabilities in response")
    doc.add_page_break()


def chapter_17(doc):
    h(doc, "17. Glossary of Technical Terms", 1)
    table(
        doc,
        ["Term", "Meaning in this project"],
        [
            ["AIA", "Audience Insight Analyst role + /aia services"],
            ["CAE", "Content Adaptation Editor + adaptation ML/services"],
            ["RBAC", "Role-based access via ROLE_CAPABILITIES"],
            ["Capability", "String permission like publish, ingest, pitch_review"],
            ["DAO", "Data Access Object — SQL for one table"],
            ["Entity", "Dataclass mirroring a table row"],
            ["Repository", "Coordinates multiple DAOs for one use case"],
            ["ETL", "Extract-Transform-Load: ingest → clean → persist"],
            ["raw_ingest", "Staging table for CSV rows pre/post cleaning"],
            ["JWT", "Signed access token (HS256) returned as session_token"],
            ["jti", "JWT ID used for logout denylist (_REVOKED_JTI)"],
            ["NEWSROOM_JWT_SECRET", "Required .env signing secret (no code fallback)"],
            ["Bearer token", "Authorization header scheme carrying the JWT"],
            ["Pydantic", "Data validation library behind request bodies"],
            ["TF-IDF", "Term frequency–inverse document frequency vectors"],
            ["Cosine similarity", "Angle-based similarity between vectors"],
            ["joblib", "Serializer for sklearn/xgboost pipelines"],
            ["PBKDF2", "Password-Based Key Derivation Function 2"],
            ["RealDictCursor", "psycopg2 cursor returning dict-like rows"],
            ["OpenAPI/Swagger", "Auto API docs at /docs"],
            ["Uvicorn", "ASGI server hosting FastAPI"],
            ["Façade", "Module wrapping services with auth/capability"],
            ["Fallback model", "Non-ML default when artifact missing"],
            ["Platform limits", "Max sentences kept per CAE target platform"],
            ["Desk profile", "1:1 extension table off users (journalist, editor, ...)"],
            ["Session TTL", "12h JWT exp (SESSION_TTL_HOURS)"],
            ["only_new", "Ingest flag: hash-changed CSVs only"],
            ["rework", "Content status sent back to journalist"],
        ],
    )
    doc.add_page_break()


def chapter_18(doc):
    h(doc, "18. Final Application Knowledge Assessment", 1)

    h(doc, "18.1 Concepts You Must Understand", 2)
    bullet(doc, "Layered request path and where RBAC is enforced.")
    bullet(doc, "Difference between modules and services.")
    bullet(doc, "Content vs news vs article vs evidence relationships.")
    bullet(doc, "ETL hash-skip and cleaner stage order.")
    bullet(doc, "Which ML pieces are trained vs heuristic.")
    bullet(doc, "Why published content matters for relevancy.")

    h(doc, "18.2 Questions (answers are in this document)", 2)
    numbered(doc, "Which FK does content.author_id reference, and why does JournalistModule call ensure_for_user?")
    numbered(doc, "What HTTP status does a missing CAE model typically surface through ValidationError mapping?")
    numbered(doc, "Name the four default cleaner stages in order.")
    numbered(doc, "Which capability does POST /cae/adaptations require?")
    numbered(doc, "Where are API sessions stored, and what happens on process restart?")
    numbered(doc, "How does publisher publish change the content row?")
    numbered(doc, "Why is /admin/raw-ingest not under /journalist?")
    numbered(doc, "What training tables feed urgency vs CAE?")
    numbered(doc, "Which file serves the non-Swagger tester UI?")
    numbered(doc, "What does pipeline_file_by_file change in AdminModule.run_pipeline?")

    h(doc, "18.3 Practical Coding Exercises", 2)
    bullet(doc, "Add GET /publisher/articles/{id} returning preview fields only.")
    bullet(doc, "Add soft validation warning when evidence text is empty but still allow create.")
    bullet(doc, "Log capability checks at INFO without printing tokens.")

    h(doc, "18.4 Flow Tracing Exercises", 2)
    bullet(doc, "Trace POST /journalist/credibility from router to evidence DAO to summary string.")
    bullet(doc, "Trace --init-db from argparse to seed_demo_users profile ensures.")
    bullet(doc, "Trace easy.html login localStorage keys through a second endpoint call.")

    h(doc, "18.5 Debugging Exercises", 2)
    bullet(doc, "Logout a JWT then reuse it; observe 401 from jti denylist.")
    bullet(doc, "Call CAE without artifacts; confirm 503 path.")
    bullet(doc, "Submit content with body length 10; observe 422 field error.")

    h(doc, "18.6 Final Checklist", 2)
    for item in [
        "I can draw the layer diagram from memory.",
        "I can list all role codes and their capabilities.",
        "I can name every router prefix and its purpose.",
        "I can explain content status transitions.",
        "I can run init-db, API, console, and pytest.",
        "I can locate urgency and CAE artifacts on disk.",
        "I can add an endpoint following existing patterns.",
        "I can diagnose 401 vs 403 vs 422 vs 503.",
        "I understand JWT login/logout (jti denylist) and that NEWSROOM_JWT_SECRET is required.",
        "I understand what is implemented vs missing (no category model endpoint, no ORM).",
        "I could rebuild a similar newsroom backend with these patterns.",
    ]:
        bullet(doc, "☐ " + item)
    doc.add_page_break()


def appendices(doc):
    h(doc, "Appendix A — Endpoint Quick Reference", 1)
    table(
        doc,
        ["Method", "Path", "Capability / notes"],
        [
            ["POST", "/auth/login", "Public"],
            ["POST", "/auth/logout", "Bearer"],
            ["POST", "/auth/change-password", "Bearer"],
            ["POST", "/auth/admin/reset-password", "manage_users"],
            ["*", "/journalist/*", "journalist_tools"],
            ["*", "/aia/*", "analytics"],
            ["*", "/cae/*", "adapt"],
            ["*", "/publisher/*", "publish"],
            ["*", "/editor/*", "pitch_review / content_review / assign"],
            ["*", "/manager/*", "pitch_review / content_review / assign / analytics"],
            ["*", "/admin/ingest*|clean|persist|pipeline|csv|raw", "ingest/clean/persist/pipeline"],
            ["POST/GET", "/admin/users*", "manage_users"],
            ["POST", "/admin/categories", "analytics"],
            ["GET", "/easy", "static HTML"],
        ],
    )

    h(doc, "Appendix B — Diagram Index", 1)
    bullet(doc, "documentation/diagrams/01_architecture.mmd — system layers")
    bullet(doc, "documentation/diagrams/02_etl_pipeline.mmd — ingest/clean/persist")
    bullet(doc, "documentation/diagrams/03_newsroom_flow.mmd — desk sequence")
    bullet(doc, "documentation/diagrams/04_erd_overview.mmd — core ER relationships")
    p(doc, "Open .mmd files in any Mermaid live editor or VS Code Mermaid preview.")

    h(doc, "Appendix C — Demo Users (passwords redacted)", 1)
    table(
        doc,
        ["Username", "role_code", "Password source"],
        [
            ["admin", "administrator", "DEMO_PASSWORDS['admin'] in constants"],
            ["analyst", "audience_insight_analyst", "DEMO_PASSWORDS"],
            ["journalist", "journalist", "DEMO_PASSWORDS"],
            ["editor", "editor", "DEMO_PASSWORDS"],
            ["adapter", "content_adaptation_editor", "DEMO_PASSWORDS"],
            ["publisher", "publisher", "DEMO_PASSWORDS"],
            ["manager", "newsroom_manager", "DEMO_PASSWORDS"],
        ],
    )
    note(doc, "See README.md or local .env/demo constants on your machine; do not paste production secrets into documents.")

    h(doc, "Closing", 1)
    p(
        doc,
        "You now have a single guide tying NewsMind AI V2’s architecture, folders, concepts, "
        "endpoints, database, validation, flows, configuration, UI bridge, libraries, tests, "
        "file-level code, design choices, exercises, glossary, and assessment together. Study "
        "with the repository open: every claim here is meant to be verified against the actual "
        "source under NewsMindAI V2/.",
    )
