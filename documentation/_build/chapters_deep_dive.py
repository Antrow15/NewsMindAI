"""Deep code walkthroughs with actual repository snippets."""

from __future__ import annotations

from pathlib import Path

from docx_helpers import bullet, code, h, note, p, table

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str, max_lines: int | None = None) -> str:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if max_lines is not None:
        lines = lines[:max_lines]
        if len(text.splitlines()) > max_lines:
            lines.append(f"# ... truncated; see full file {rel} ({len(text.splitlines())} lines)")
    return "\n".join(lines)


def _file_section(doc, rel: str, purpose: str, *, max_lines: int = 80, explain: list[str] | None = None):
    h(doc, rel, 3)
    p(doc, f"Purpose: {purpose}")
    p(doc, f"Absolute project path: NewsMindAI V2/{rel}")
    code(doc, _read(rel, max_lines=max_lines))
    for line in explain or []:
        bullet(doc, line)


def chapter_deep_dive(doc):
    h(doc, "14B. Expanded Source Walkthroughs (Actual Code)", 1)
    p(
        doc,
        "This section embeds real source from the repository (truncated only when files are long). "
        "Use it alongside Chapter 14. Do not treat these snippets as substitutes for opening the files "
        "in your IDE while learning.",
    )

    h(doc, "14B.1 Configuration & Database Core", 2)
    _file_section(
        doc,
        "config/env_loader.py",
        "Loads .env once into os.environ without python-dotenv dependency.",
        max_lines=40,
        explain=[
            "ROOT points at project root via Path(__file__).parents[1].",
            "_LOADED prevents double-loading; existing os.environ keys win (do not override).",
            "Comments and blank lines skipped; quotes stripped from values.",
        ],
    )
    _file_section(
        doc,
        "config/db_config.py",
        "Frozen DatabaseConfig dataclass + loader for psycopg2 connect kwargs.",
        max_lines=55,
        explain=[
            "dsn_kwargs includes keepalives for hosted Postgres.",
            "Defaults exist for local demo; production should set env explicitly.",
        ],
    )
    _file_section(
        doc,
        "database/connection.py",
        "Connection helpers, SQL apply, schema require, init_schema.",
        max_lines=100,
        explain=[
            "db_cursor uses connection context manager (commit) then closes.",
            "RealDictCursor makes rows dict-like for DAOs.",
            "apply_sql_file strips -- comments then splits on semicolons.",
            "init_schema is destructive: applies newsmind.sql then seeds demos.",
        ],
    )

    h(doc, "14B.2 Security & Auth", 2)
    _file_section(
        doc,
        "modules/authentication/security.py",
        "PBKDF2 password hashing and JWT create/decode (PyJWT HS256).",
        explain=[
            "Stored form salt_hex$digest_hex matches single ERD password_hash column.",
            "verify_password fails closed on malformed hashes.",
            "hmac.compare_digest resists timing attacks.",
            "create_access_token / decode_access_token use get_jwt_secret() from .env.",
        ],
    )
    _file_section(
        doc,
        "modules/authentication/auth_service.py",
        "Login, JWT resolve, logout (jti denylist), password change/reset.",
        max_lines=120,
        explain=[
            "Access tokens are JWTs; restart does not invalidate unexpired JWTs unless secret changes.",
            "Logout adds jti to _REVOKED_JTI (process-local) until exp.",
            "CLI file logs/.session_token stores last JWT for console resolve_session().",
            "capabilities attached from ROLE_CAPABILITIES after DB user reload.",
            "ip_address/user_agent accepted but unused (reserved).",
        ],
    )
    _file_section(
        doc,
        "api/deps.py",
        "FastAPI Depends chain for Bearer session tokens.",
        explain=[
            "HTTPBearer(auto_error=False) enables custom 401 detail text.",
            "get_current_user used by change-password; most routes use get_session_token + capability.",
        ],
    )

    h(doc, "14B.3 API Surface Sample", 2)
    _file_section(
        doc,
        "api/main.py",
        "FastAPI factory, CORS, exception handlers, router registration, /easy.",
        max_lines=175,
        explain=[
            "lifespan loads dotenv at startup.",
            "RequestValidationError reshaped into field errors list.",
            "AppError handler calls raise_http_error then returns JSON.",
            "Routers included in pedagogical OpenAPI tag order.",
        ],
    )
    _file_section(
        doc,
        "api/http_errors.py",
        "Central mapping from domain exceptions to HTTPException.",
        explain=[
            "Always raises — callers use bare raise_http_error(exc) in except blocks.",
            "Special-case ValidationError containing 'No trained model' → 503.",
        ],
    )
    _file_section(
        doc,
        "api/routers/auth.py",
        "Auth HTTP endpoints.",
        max_lines=90,
        explain=[
            "login catches AuthenticationError → 401 directly.",
            "admin reset uses CAP_MANAGE_USERS via require_capability_session.",
        ],
    )
    _file_section(
        doc,
        "api/routers/journalist.py",
        "Journalist tools + desk endpoints.",
        max_lines=100,
        explain=[
            "_tools(token) constructs JournalistModule per request.",
            "All handlers share _APP_ERRORS → raise_http_error pattern.",
        ],
    )

    h(doc, "14B.4 Schemas & Rules", 2)
    _file_section(
        doc,
        "api/schemas/rules.py",
        "Shared Annotated / AfterValidator types for API bodies.",
        max_lines=120,
        explain=[
            "StrongPasswordStr delegates to require_password.",
            "ContentStatusStr lowercases and checks ALLOWED_CONTENT_STATUSES.",
            "Keeps routers free of duplicated Field constraints.",
        ],
    )

    h(doc, "14B.5 Services & Modules", 2)
    _file_section(
        doc,
        "services/access.py",
        "Session resolve + capability check used across API and modules.",
    )
    _file_section(
        doc,
        "services/permission_service.py",
        "RBAC helpers over ROLE_CAPABILITIES.",
        explain=["Administrator short-circuits has_capability to True."],
    )
    _file_section(
        doc,
        "modules/journalist/journalist_module.py",
        "Journalist façade with author_id mapping and tools.",
        max_lines=150,
        explain=[
            "author_id must be journalist_id FK, not user_id.",
            "credibility loads content body + attached evidence only.",
            "related_content delegates to ml.knowledge.score_content_relevancy.",
        ],
    )
    _file_section(
        doc,
        "modules/admin/admin_module.py",
        "ETL orchestration façade.",
        max_lines=160,
        explain=[
            "injectable services enable testing.",
            "ingest optionally persists raw_ingest pending rows.",
            "clean always produces content_stats + optional cleaning_report_id.",
        ],
    )
    _file_section(
        doc,
        "services/ingestion_service.py",
        "CSV discovery, hashing, chunked read, normalize.",
        max_lines=120,
        explain=[
            "Path traversal blocked by resolving under data/raw.",
            "MD5 file hash for change detection (integrity of ingest skip, not password security).",
            "Rows without title dropped from usable set.",
        ],
    )
    _file_section(
        doc,
        "services/content/content_service.py",
        "Validated content domain operations.",
        max_lines=130,
        explain=[
            "News/article creation requires ≥1 evidence item.",
            "Creates content row then specialized news/article row.",
        ],
    )

    h(doc, "14B.6 Cleaners", 2)
    _file_section(
        doc,
        "cleaners/stages/base_cleaner.py",
        "CleanerResult + BaseCleaner abstract stage.",
    )
    _file_section(
        doc,
        "cleaners/pipeline.py",
        "Ordered execution of cleaner stages with aggregated stats.",
    )
    _file_section(
        doc,
        "cleaners/orchestrator.py",
        "Public clean_content/clean_pitches API used by AdminModule.",
    )

    h(doc, "14B.7 Persistence Layer", 2)
    _file_section(
        doc,
        "dao/base_dao.py",
        "Shared execute/get/delete/list helpers.",
        explain=["table attribute set by subclasses; SQL is string-built with care on identifiers."],
    )
    _file_section(
        doc,
        "repository/content_repository.py",
        "Multi-DAO content aggregate.",
    )
    _file_section(
        doc,
        "entities/content/content.py",
        "Content dataclass payload.",
    )
    _file_section(
        doc,
        "entities/user.py",
        "User dataclass including joined role fields used after reads.",
    )

    h(doc, "14B.8 Desk Services", 2)
    for rel, purpose in [
        ("services/editor/editor_service.py", "Editorial queue, urgency, assignments."),
        ("services/manager/manager_service.py", "Ops analytics + editor delegation."),
        ("services/publisher/publisher_service.py", "Publication lifecycle."),
        ("services/aia/aia_service.py", "Audience scores and pitches."),
        ("services/adaptation/adaptation_service.py", "Create multi-platform adaptations."),
        ("services/adaptation/review_service.py", "Approve/reject/regenerate/finalize drafts."),
    ]:
        _file_section(doc, rel, purpose, max_lines=90)

    h(doc, "14B.9 ML", 2)
    for rel, purpose in [
        ("ml/common/similarity.py", "TF-IDF rank and similar_pairs."),
        ("ml/knowledge/base.py", "Published-content relevancy corpus."),
        ("ml/aia/audience_scores.py", "Heuristic engagement/interest/trend."),
        ("ml/editor/queue_urgency.py", "Urgency model load + predict."),
        ("ml/adaptation/predict.py", "CAE sentence retention inference."),
        ("ml/training/console.py", "Push/train CLI orchestration."),
    ]:
        _file_section(doc, rel, purpose, max_lines=80)

    h(doc, "14B.10 Journalist tool services", 2)
    for rel, purpose in [
        ("services/journalist/content_validate.py", "Validate + relevancy wrapper."),
        ("services/journalist/credibility.py", "Claim splitting vs evidence."),
        ("services/journalist/duplicate_check.py", "Near-duplicate pairs."),
        ("services/journalist/evidence_search.py", "Rank evidence docs."),
    ]:
        _file_section(doc, rel, purpose, max_lines=80)

    h(doc, "14B.11 Utils", 2)
    _file_section(doc, "utils/errors.py", "AppError hierarchy.")
    _file_section(
        doc,
        "utils/validators.py",
        "Shared field validators for services/cleaners/DAOs.",
        max_lines=120,
    )
    _file_section(doc, "utils/logger.py", "Logger factory.")
    _file_section(doc, "utils/csv_fields.py", "CSV column alias normalization.", max_lines=80)

    h(doc, "14B.12 Constants (RBAC excerpt)", 2)
    _file_section(
        doc,
        "config/constants.py",
        "Roles, capabilities, platforms, security constants, demo password map.",
        max_lines=145,
        explain=[
            "DEMO_PASSWORDS are for local bootstrap only.",
            "ROLE_CAPABILITIES is the authorization source of truth.",
        ],
    )

    h(doc, "14B.13 Tests & Frontend Bridge", 2)
    _file_section(doc, "tests/conftest.py", "Path fix + db_ready fixture.")
    note(
        doc,
        "api/static/easy.html is ~1000+ lines of HTML/JS. Open it in an editor; it defines "
        "api(), login, GROUPS endpoint forms, and localStorage session keys nm_token/nm_user/nm_role.",
    )
    p(doc, "Excerpt — how easy.html calls the API (conceptual structure from source):")
    code(
        doc,
        "async function api(method, path, body) {\n"
        "  const headers = { 'Content-Type': 'application/json' };\n"
        "  if (state.token) headers['Authorization'] = 'Bearer ' + state.token;\n"
        "  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });\n"
        "  ...\n"
        "}\n"
        "// Login: POST /auth/login → save session_token to localStorage\n"
        "// GROUPS[] maps UI sections to method+path+fields for every desk",
    )

    h(doc, "14B.14 SQL Schema Head", 2)
    p(doc, "Opening of database/newsmind.sql showing bootstrap + core RBAC tables:")
    code(doc, _read("database/newsmind.sql", max_lines=120))

    h(doc, "14B.15 Import Dependency Matrix (selected)", 2)
    table(
        doc,
        ["Consumer", "Produces / depends on"],
        [
            ["api.routers.*", "schemas, deps, services/modules, http_errors"],
            ["modules.admin", "ingestion, cleaners, persistence, report, access"],
            ["modules.journalist", "ContentService, journalist services, JournalistDAO"],
            ["services.*", "dao/repository/ml/validators"],
            ["dao.*", "database.connection, entities, validators"],
            ["cleaners.*", "utils.helpers/validators, config.constants"],
            ["ml.training", "cleaners, DB staging tables, sklearn/xgboost"],
            ["app.py", "modules, services.user, database, console_ui"],
        ],
    )
    doc.add_page_break()
