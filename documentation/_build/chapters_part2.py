"""Chapters 6–11 of the NewsMind V2 learning guide."""

from __future__ import annotations

from docx_helpers import bullet, code, h, note, numbered, p, table


def _endpoint(doc, method, path, purpose, file, handler, service, auth, body, response, flow):
    h(doc, f"{method} {path}", 3)
    table(
        doc,
        ["Aspect", "Detail"],
        [
            ["Purpose", purpose],
            ["Defined in", file],
            ["Handler", handler],
            ["Calls", service],
            ["Auth", auth],
            ["Body / params", body],
            ["Success response", response],
        ],
    )
    p(doc, f"Execution flow: {flow}")


def chapter_6(doc):
    h(doc, "6. Every API Endpoint in Detail", 1)
    p(
        doc,
        "All routes below are registered from api/main.py via include_router. Unless noted, "
        "Authorization: Bearer <session_token> is required. Validation failures return HTTP 422 "
        "with {detail, errors:[{field,message}]}. Auth failures return 401. Capability failures "
        "return 403. Missing entities return 404. Missing trained models may return 503.",
    )

    h(doc, "6.1 Auth — prefix /auth", 2)
    _endpoint(
        doc, "POST", "/auth/login", "Create session",
        "api/routers/auth.py", "login", "authenticate()",
        "None (public)", "LoginRequest: username, password",
        "LoginResponse: session_token, user_id, username, role_code, capabilities",
        "Body → authenticate → UserDAO → verify_password → token → LoginResponse",
    )
    code(
        doc,
        "Example request:\n"
        "POST /auth/login\n"
        '{"username":"journalist","password":"<DEMO_PASSWORD>"}\n\n'
        "Example success:\n"
        '{"session_token":"<TOKEN>","user_id":3,"username":"journalist",'
        '"role_code":"journalist","capabilities":["ingest","clean","persist","pipeline","journalist_tools"]}\n\n'
        "Example failure (401):\n"
        '{"detail":"Invalid username or password."}',
    )
    _endpoint(
        doc, "POST", "/auth/logout", "Invalidate session token",
        "auth.py", "do_logout", "logout(token)",
        "Bearer required", "none", "MessageResponse",
        "Bearer JWT → logout revokes jti in _REVOKED_JTI (+ clear CLI file if match)",
    )
    _endpoint(
        doc, "POST", "/auth/change-password", "User changes own password",
        "auth.py", "do_change_password", "change_password",
        "Bearer + any logged-in user", "current_password, new_password (strong)",
        "MessageResponse",
        "get_current_user → verify current → hash new → UserDAO.update_password_hash",
    )
    _endpoint(
        doc, "POST", "/auth/admin/reset-password", "Admin resets any user password",
        "auth.py", "do_admin_reset_password", "UserService.reset_password",
        "Bearer + CAP_MANAGE_USERS", "username, new_password",
        "MessageResponse",
        "require_capability_session(manage_users) → reset hash",
    )

    h(doc, "6.2 Journalist — prefix /journalist (CAP_JOURNALIST_TOOLS)", 2)
    p(doc, "Facade: JournalistModule(session_token=token). Roles with journalist_tools: journalist, admin.")
    for method, path, purpose, svc in [
        ("POST", "/journalist/duplicates", "Find near-duplicate document pairs", "find_duplicates → ml.common.similar_pairs"),
        ("POST", "/journalist/validate", "Validate fields + relevancy", "validate_article → knowledge score"),
        ("POST", "/journalist/related-content", "Related published content", "score_content_relevancy"),
        ("POST", "/journalist/credibility", "Claims vs attached evidence", "assess_credibility after list_evidence"),
        ("POST", "/journalist/news", "Create news + required evidence", "ContentService.add_news"),
        ("POST", "/journalist/articles", "Create article + required evidence", "ContentService.add_article"),
        ("GET", "/journalist/content", "List content (limit, status)", "list_content"),
        ("GET", "/journalist/content/{content_id}", "Get one content row", "get_content"),
        ("PUT", "/journalist/content/{content_id}/status", "Update status", "update_content_status"),
        ("GET", "/journalist/news", "List news kind", "list_news"),
        ("POST", "/journalist/evidence", "Attach evidence", "add_evidence"),
        ("GET", "/journalist/content/{content_id}/evidence", "List evidence", "list_evidence"),
    ]:
        bullet(doc, f"{method} {path} — {purpose} — {svc}")

    code(
        doc,
        "Create news example:\n"
        "POST /journalist/news\n"
        "Authorization: Bearer <TOKEN>\n"
        "{\n"
        '  "title": "Metro bridge inspection delay",\n'
        '  "body": "City engineers postponed the scheduled inspection after ... (40+ chars)",\n'
        '  "summary": "Inspection delayed",\n'
        '  "severity": "medium",\n'
        '  "breaking": false,\n'
        '  "status": "draft",\n'
        '  "evidence": [{"title": "Memo", "evidence_type": "document", "text": "Official notice..." }]\n'
        "}\n\n"
        "Validation failure (422) if title too short or evidence missing.\n"
        "Credibility failure (400) if no evidence attached.",
    )

    h(doc, "6.3 AIA — prefix /aia (CAP_ANALYTICS)", 2)
    for row in [
        ("POST", "/aia/analyze-engagement", "Heuristic engagement from views/likes/shares/comments"),
        ("POST", "/aia/analyze-interest", "Heuristic interest score"),
        ("POST", "/aia/analyze-trends", "Trend score from title/summary text"),
        ("GET", "/aia/performance", "Publication → AIA performance analytics loop"),
        ("POST", "/aia/generate-story-pitch", "Persist AI_GENERATED story_pitch with scores"),
        ("GET", "/aia/story-pitches", "List pitches"),
        ("GET", "/aia/story-pitches/top", "Top pitches"),
    ]:
        bullet(doc, f"{row[0]} {row[1]} — {row[2]}")
    note(doc, "There is no category prediction endpoint; category on pitches is manual entry.")

    h(doc, "6.4 CAE — prefix /cae (CAP_ADAPT)", 2)
    for row in [
        ("POST", "/cae/adaptations", "201 — create request + platform drafts via ML"),
        ("GET", "/cae/adaptations/{request_id}", "Fetch request + drafts"),
        ("POST", "/cae/adaptation-drafts/{draft_id}/approve", "Approve draft"),
        ("POST", "/cae/adaptation-drafts/{draft_id}/reject", "Reject (remarks required)"),
        ("POST", "/cae/adaptation-drafts/{draft_id}/regenerate", "201 — new version from remarks"),
        ("PUT", "/cae/adaptation-drafts/{draft_id}/final", "Finalize title/content → final_adaptations"),
        ("GET", "/cae/adaptation-drafts/{draft_id}/versions", "List version chain"),
    ]:
        bullet(doc, f"{row[0]} {row[1]} — {row[2]}")
    p(
        doc,
        "Platforms must be from ADAPTATION_PLATFORMS: SOCIAL_MEDIA, PRINT_NEWSPAPER, WEBSITE, "
        "EMAIL_NEWSLETTER. Flow: AdaptationService.create → AdaptationDAO + predict_sentences + "
        "format_output + validate_facts → drafts; ReviewService for human actions.",
    )

    h(doc, "6.5 Publisher — prefix /publisher (CAP_PUBLISH)", 2)
    for row in [
        ("GET", "/publisher/articles", "Ready/approved queue"),
        ("PUT", "/publisher/articles/{content_id}/approve", "Ensure publication row"),
        ("GET", "/publisher/templates", "PUBLICATION_TEMPLATES constants"),
        ("PUT", "/publisher/articles/{content_id}/template", "Assign template_code"),
        ("GET", "/publisher/articles/{content_id}/preview", "HTML preview string"),
        ("POST", "/publisher/articles/{content_id}/publish", "Publish now → content status published"),
        ("POST", "/publisher/articles/{content_id}/schedule", "Schedule future publish"),
        ("GET", "/publisher/analytics", "Publication status counts"),
    ]:
        bullet(doc, f"{row[0]} {row[1]} — {row[2]}")

    h(doc, "6.6 Editor — prefix /editor", 2)
    p(doc, "Capabilities vary: pitch_review, content_review, assign.")
    for row in [
        ("GET", "/editor/queue", "Merged priority queue (urgency model)"),
        ("POST", "/editor/queue/score", "Score urgency for title/summary"),
        ("GET", "/editor/pitches", "List pitches by status"),
        ("POST", "/editor/pitches/duplicates", "Duplicate pitch detection"),
        ("POST", "/editor/assign/suggest", "Suggest journalists by specialty/workload"),
        ("PUT", "/editor/pitches/{id}/approve|reject", "Pitch decisions"),
        ("GET", "/editor/content", "Content review list"),
        ("PUT", "/editor/content/{id}/approve|reject|rework", "Content decisions"),
        ("PUT", "/editor/content/{id}/assign", "Assign to journalist user"),
    ]:
        bullet(doc, f"{row[0]} {row[1]} — {row[2]}")

    h(doc, "6.7 Manager — prefix /manager", 2)
    p(
        doc,
        "Shares review actions with EditorService via ManagerService delegation, plus analytics: "
        "overview, bottlenecks, analytics, workload, deadline-risk, resources.",
    )
    for path in [
        "/manager/overview", "/manager/bottlenecks", "/manager/analytics",
        "/manager/workload", "/manager/deadline-risk", "/manager/resources",
        "/manager/queue", "/manager/pitches", "/manager/content",
        "/manager/pitches/{id}/approve|reject",
        "/manager/content/{id}/approve|reject|assign",
    ]:
        bullet(doc, path)

    h(doc, "6.8 Admin — prefix /admin", 2)
    for row in [
        ("GET", "/admin/csv-files", "List data/raw CSVs + new/changed"),
        ("GET", "/admin/raw-ingest", "ETL staging rows (not journalist)"),
        ("POST", "/admin/ingest", "Ingest CSVs (only_new flag)"),
        ("POST", "/admin/ingest-file", "Ingest one relative CSV path"),
        ("POST", "/admin/clean", "Clean loaded data"),
        ("POST", "/admin/ingest-and-clean", "Combined"),
        ("POST", "/admin/persist", "Persist cleaned"),
        ("POST", "/admin/pipeline", "Full ETL"),
        ("POST", "/admin/users", "Create user (manage_users)"),
        ("POST", "/admin/users/reset-password", "Reset password"),
        ("GET", "/admin/users/{username}", "Lookup user"),
        ("POST", "/admin/categories", "Add category (CAP_ANALYTICS)"),
    ]:
        bullet(doc, f"{row[0]} {row[1]} — {row[2]}")

    h(doc, "6.9 Utility routes", 2)
    bullet(doc, "GET /easy — FileResponse easy.html (not in OpenAPI schema).")
    bullet(doc, "GET /docs — Swagger UI.")
    bullet(doc, "OpenAPI JSON at /openapi.json (FastAPI default).")

    h(doc, "6.10 Who Calls What", 2)
    p(
        doc,
        "easy.html GROUPS config calls essentially the full surface above. Console app.py calls "
        "AdminModule/ContentModule/UserService directly (no HTTP). pytest TestClient hits the same "
        "routers. Internal services do not HTTP-call each other.",
    )
    doc.add_page_break()


def chapter_7(doc):
    h(doc, "7. Database Models, Schemas, and Queries", 1)

    h(doc, "7.1 Technology and Connection", 2)
    p(
        doc,
        "PostgreSQL via psycopg2. Config from NEWSROOM_DB_* env vars through DatabaseConfig.dsn_kwargs "
        "(host, port, dbname, user, password, connect_timeout, sslmode, TCP keepalives). "
        "db_cursor commits on success and always closes the connection.",
    )

    h(doc, "7.2 Bootstrap Lifecycle", 2)
    numbered(doc, "python app.py --init-db → init_schema().")
    numbered(doc, "apply_sql_file(database/newsmind.sql) — DROP SCHEMA public CASCADE then recreate.")
    numbered(doc, "seed_demo_users() creates 7 employees/users/desk profiles.")
    numbered(doc, "Optional: apply seed_temp_data.sql for metro probe content.")
    note(doc, "init-db is destructive to the public schema. Never run against production blindly.")

    h(doc, "7.3 Core Tables", 2)
    table(
        doc,
        ["Table", "PK", "Key fields / relationships"],
        [
            ["employee", "employee_id", "HR identity; unique email, employee_code"],
            ["role", "role_id", "role_code unique (administrator, journalist, ...)"],
            ["users", "user_id", "FK employee, FK role; username; password_hash; account_status"],
            ["journalist/editor/publisher/...", "desk PK", "1:1 users; desk-specific columns"],
            ["category", "category_id", "category_name unique"],
            ["story_pitch", "story_pitch_id", "scores, priority, status, created_by"],
            ["content", "content_id", "author_id→journalist; status; kind article|news"],
            ["article", "article_id", "1:1 content; story_pitch_id optional"],
            ["news", "news_id", "1:1 content; event_*, severity, breaking"],
            ["evidence", "evidence_id", "FK content; ocr_text; uploaded_by"],
            ["raw_ingest", "raw_ingest_id", "staging; cleaning_status; optional content_id"],
            ["ingest_file", "ingest_file_id", "source_file unique + file_hash"],
            ["cleaning_report", "cleaning_report_id", "report_json JSONB"],
            ["publication", "publication_id", "1:1 content; template; schedule"],
            ["adaptation_*", "id", "requests, drafts, reviews, finals"],
            ["ml_train_*", "id", "urgency/adaptation/category training staging"],
        ],
    )

    h(doc, "7.4 Content Status Lifecycle", 2)
    code(doc, "draft → submitted → approved|rejected|rework → published\nAllowed: draft, submitted, approved, rejected, published, rework")

    h(doc, "7.5 Entity Example — Content", 2)
    code(
        doc,
        "@dataclass\n"
        "class Content:\n"
        "    content_id: Optional[int] = None\n"
        "    author_id: Optional[int] = None  # journalist.journalist_id\n"
        "    title: str = \"\"\n"
        "    summary: Optional[str] = None\n"
        "    raw_body / content_body\n"
        "    content_kind: Optional[str] = \"article\"\n"
        "    status: str = \"draft\"\n"
        "    current_version: int = 1",
    )
    p(
        doc,
        "ContentService.add_news builds Content(kind=news) then News child then evidence rows. "
        "ContentRepository.save_content_bundle chooses Article vs News from content_kind.",
    )

    h(doc, "7.6 Indexes and Constraints", 2)
    bullet(doc, "Unique: usernames, emails, role_code, category_name, ingest source_file.")
    bullet(doc, "FK cascades: deleting content removes article/news/evidence/publication.")
    bullet(doc, "Indexes: raw_ingest.cleaning_status, content.status, publication.status, adaptation drafts.")
    bullet(doc, "Unique index on ml_train_adaptation (source_file, article_id, target_platform).")

    h(doc, "7.7 CRUD Path Example", 2)
    code(
        doc,
        "JournalistModule.add_news(**fields)\n"
        "  → ContentService.add_news\n"
        "      validate title/body/status/evidence\n"
        "      ContentDAO.create(Content(...))  INSERT content RETURNING id\n"
        "      NewsDAO.create(News(...))\n"
        "      EvidenceDAO.create for each evidence item\n"
        "  → JSON {content_id, news_id, evidence_ids, ...}",
    )
    note(doc, "ER diagram source: documentation/diagrams/04_erd_overview.mmd")
    doc.add_page_break()


def chapter_8(doc):
    h(doc, "8. Validation and Error Handling", 1)

    h(doc, "8.1 Layers of Validation", 2)
    numbered(doc, "Pydantic schemas (API): lengths, enums via AfterValidator, strong passwords.")
    numbered(doc, "utils.validators (domain): require_* helpers raising ValidationError.")
    numbered(doc, "Cleaner SchemaCleaner: rejects bad CSV rows during ETL.")
    numbered(doc, "Business rules: e.g., evidence required for news/article create; credibility needs evidence.")
    numbered(doc, "RBAC: PermissionDeniedError → 403.")
    numbered(doc, "Auth: AuthenticationError/AuthError → 401.")

    h(doc, "8.2 Password Rules", 2)
    p(
        doc,
        "require_password / StrongPasswordStr: minimum 10 characters, uppercase, lowercase, digit, "
        "special character; no leading/trailing spaces; max 128. LoginPasswordStr only requires "
        "non-empty for login (so existing users can still authenticate).",
    )

    h(doc, "8.3 Global API Handlers", 2)
    bullet(doc, "RequestValidationError → 422 {detail: Validation failed, errors:[{field,message}]}")
    bullet(doc, "HTTPException → {detail}")
    bullet(doc, "AppError → raise_http_error mapping")
    bullet(doc, "AuthenticationError → 401")
    bullet(doc, "Exception → 500 logged with log.exception")

    h(doc, "8.4 raise_http_error Mapping", 2)
    table(
        doc,
        ["Exception", "HTTP"],
        [
            ["AuthError / AuthenticationError", "401"],
            ["PermissionDeniedError", "403"],
            ["NotFoundError", "404"],
            ["FileNotFoundError", "503"],
            ["ValidationError with 'No trained model'", "503"],
            ["Other ValidationError / AppError", "400"],
            ["Unknown", "500"],
        ],
    )

    h(doc, "8.5 Logging", 2)
    p(
        doc,
        "utils.logger.get_logger writes to logs/ and console. Pipeline uses utils.progress.progress "
        "for human-readable steps. Unhandled API exceptions are logged before 500 responses.",
    )
    doc.add_page_break()


def chapter_9(doc):
    h(doc, "9. Complete End-to-End Application Flows", 1)

    h(doc, "9.1 Application Startup (API)", 2)
    numbered(doc, "uvicorn loads api.main:app")
    numbered(doc, "create_app() builds FastAPI, middleware, handlers, routers")
    numbered(doc, "lifespan startup: load_dotenv(); log started")
    numbered(doc, "First DB use: load_db_config → psycopg2.connect")
    numbered(doc, "First ML predict: joblib load into lru_cache")
    p(doc, "Shutdown: lifespan yields end (no explicit pool close—connections are per-call).")

    h(doc, "9.2 Application Startup (Console)", 2)
    numbered(doc, "python app.py → load_dotenv at import; AdminModule/ContentModule/UserService singletons")
    numbered(doc, "interactive() builds role menu from resolve_session() + capabilities")
    numbered(doc, "--init-db runs init_schema")

    h(doc, "9.3 Flow: Login → Create News → Submit → Approve → Publish", 2)
    code(
        doc,
        "1. POST /auth/login as journalist → session_token\n"
        "2. POST /journalist/news with evidence → content_id (status draft)\n"
        "3. PUT /journalist/content/{id}/status {\"status\":\"submitted\"}\n"
        "4. Login as editor → GET /editor/queue (urgency ordered)\n"
        "5. PUT /editor/content/{id}/approve\n"
        "6. Login as publisher → PUT /publisher/articles/{id}/approve\n"
        "7. POST /publisher/articles/{id}/publish → content.status=published\n"
        "8. Login as analyst → GET /aia/performance sees published loop data\n"
        "9. Related-content/relevancy now includes this article in corpus",
    )

    h(doc, "9.4 Flow: Admin ETL Pipeline", 2)
    code(
        doc,
        "AdminModule.run_pipeline(only_new=...)\n"
        "  if pipeline_file_by_file:\n"
        "    for each CSV: ingest_file → clean → persist\n"
        "    then pitches.csv batch\n"
        "  else:\n"
        "    ingest_and_clean → persist\n"
        "Side effects: ingest_file hash rows, raw_ingest, cleaning_report, content rows",
    )

    h(doc, "9.5 Flow: CAE Adaptation", 2)
    code(
        doc,
        "POST /cae/adaptations {title, content, target_platforms}\n"
        "  → AdaptationDAO.create_request\n"
        "  → for platform: predict_sentences → format_output → validate_facts → create_draft\n"
        "POST approve / reject / regenerate\n"
        "PUT final → final_adaptations + draft status FINALIZED",
    )

    h(doc, "9.6 Flow: ML Training", 2)
    code(
        doc,
        "python -m ml.training --push-only   # CSV → ml_train_urgency / ml_train_adaptation\n"
        "python -m ml.training --all --fast  # train models → artifacts/models/...\n"
        "Console admin menu ML TRAINING does push+train with hash skip",
    )

    h(doc, "9.7 Error Path Example", 2)
    p(
        doc,
        "Publisher tries publish on non-approved content → ValidationError/NotFound style domain "
        "error → router except → raise_http_error → JSON error to easy.html which displays detail.",
    )
    doc.add_page_break()


def chapter_10(doc):
    h(doc, "10. Configuration and Environment Variables", 1)
    note(doc, "Never commit real production secrets. Values below use placeholders.")

    table(
        doc,
        ["Variable", "Controls", "If changed"],
        [
            ["NEWSROOM_DB_HOST/PORT/NAME/USER/PASSWORD", "Postgres connection", "Connect elsewhere / auth fail"],
            ["NEWSROOM_DB_SSLMODE", "SSL mode (prefer/require/...)", "Cloud Postgres often needs require"],
            ["NEWSROOM_DB_CONNECT_TIMEOUT", "Connect timeout seconds", "Fail faster/slower"],
            ["NEWSROOM_DEBUG", "Debug flag (available)", "App-specific debug behavior"],
            ["NEWSROOM_JWT_SECRET", "JWT HS256 signing secret (required)", "Auth fails if unset; no code fallback"],
            ["NEWSROOM_CSV_CHUNK_ROWS", "pandas chunk size (min 500)", "Memory vs speed on large CSV"],
            ["NEWSROOM_DB_INSERT_BATCH", "Bulk insert batch (min 50)", "Insert throughput"],
            ["NEWSROOM_MAX_CSV_MB_WARN", "Warn threshold MB", "Only logging/progress"],
            ["NEWSROOM_WRITE_PROCESSED_FILES", "Write data/processed snapshots", "Disk use; DB still SoT"],
            ["NEWSROOM_PIPELINE_FILE_BY_FILE", "Per-file ETL vs bulk", "Pipeline strategy"],
        ],
    )

    h(doc, "10.1 Important Constants", 2)
    bullet(doc, "SESSION_TTL_HOURS=12, MAX_LOGIN_FAILURES=5 (constants; lockout fields reserved).")
    bullet(doc, "PASSWORD_HASH_ITERATIONS=120_000, PASSWORD_SALT_BYTES=16.")
    bullet(doc, "MIN_TITLE_LENGTH=5, MIN_BODY_LENGTH=40.")
    bullet(doc, "ADAPTATION_PLATFORMS + PLATFORM_SENTENCE_LIMITS.")
    bullet(doc, "PUBLICATION_TEMPLATES list.")
    bullet(doc, "DEMO_PASSWORDS for local demo only — treat as placeholders in docs/shared guides.")

    h(doc, "10.2 Run Commands", 2)
    code(
        doc,
        'cd "G:\\NewsMind AI\\NewsMindAI V2"\n'
        "$env:PYTHONPATH = \"G:\\NewsMind AI\\NewsMindAI V2\"\n"
        "python -m pip install -r requirements.txt\n"
        "python app.py --init-db\n"
        "python app.py\n"
        "uvicorn api.main:app --reload\n"
        "# Open http://127.0.0.1:8000/docs or /easy",
    )
    doc.add_page_break()


def chapter_11(doc):
    h(doc, "11. Frontend and Backend Integration", 1)
    p(
        doc,
        "V2 has no SPA framework. Integration clients are: (1) api/static/easy.html, "
        "(2) Swagger UI, (3) pytest httpx TestClient, (4) optional external HTTP clients.",
    )

    h(doc, "11.1 easy.html Architecture", 2)
    bullet(doc, "State: token, username, role in memory + localStorage (nm_token, nm_user, nm_role).")
    bullet(doc, "api(method, path, body) builds fetch with JSON + Bearer header.")
    bullet(doc, "GROUPS array defines sections/forms/endpoints per role.")
    bullet(doc, "readFields transforms documents_json, evidence_json, only_new, target_platforms.")
    bullet(doc, "Role gating in UI is convenience; real security is server-side capabilities.")

    h(doc, "11.2 Auth Flow in UI", 2)
    code(
        doc,
        "Login form → POST /auth/login → store JWT session_token\n"
        "Subsequent calls → Authorization: Bearer <JWT>\n"
        "Logout → POST /auth/logout → server revokes jti; clear localStorage",
    )

    h(doc, "11.3 Mapping Examples", 2)
    table(
        doc,
        ["UI section", "Backend endpoints"],
        [
            ["Journalist tools", "/journalist/duplicates, validate, related-content, credibility"],
            ["Journalist desk", "/journalist/news, articles, content, evidence, status"],
            ["AIA", "/aia/analyze-*, generate-story-pitch, story-pitches, performance"],
            ["Editor", "/editor/queue, pitches, content, assign/suggest"],
            ["CAE", "/cae/adaptations and draft actions"],
            ["Publisher", "/publisher/articles, templates, publish, schedule"],
            ["Manager", "/manager/* analytics + review"],
            ["Admin", "/admin/ingest*, clean, persist, pipeline, users, categories"],
        ],
    )

    h(doc, "11.4 Error and Loading Display", 2)
    p(
        doc,
        "easy.html shows HTTP error detail text from JSON responses. Loading is implicit around "
        "await fetch. There is no global Redux-style store—DOM updates after each call.",
    )
    doc.add_page_break()
