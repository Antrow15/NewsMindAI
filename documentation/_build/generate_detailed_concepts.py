"""Detailed concept + file/method/library guide (no full source dumps)."""

from __future__ import annotations

import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
DOC_ROOT = BUILD.parent
OUT_DOCX = DOC_ROOT / "NewsMind_Concept_And_Code_Explanation_Guide.docx"
OUT_PDF = DOC_ROOT / "NewsMind_Concept_And_Code_Explanation_Guide.pdf"

sys.path.insert(0, str(BUILD))
import docx_helpers as H  # noqa: E402
from theory_blocks import concept_block, file_block, flow  # noqa: E402


def build() -> Path:
    doc = H.setup_document()

    for _ in range(2):
        doc.add_paragraph()
    t = doc.add_paragraph()
    t.alignment = 1
    r = t.add_run("NewsMind AI V2")
    H.set_run_font(r, size=26, bold=True, color=H.NAVY)
    s = doc.add_paragraph()
    s.alignment = 1
    r = s.add_run("Concept + File / Method / Library Explanation Guide")
    H.set_run_font(r, size=16, bold=True, color=H.ACCENT)
    n = doc.add_paragraph()
    n.alignment = 1
    r = n.add_run(
        "Each concept is explained separately, then the files that implement it:\n"
        "purpose, libraries, methods, parameters, what they call, and who calls them.\n"
        "Source listings are not dumped; behavior is described."
    )
    H.set_run_font(r, size=10, italic=True, color=H.MUTED)
    doc.add_page_break()

    H.h(doc, "0. Reading pattern for every chapter", 1)
    H.numbered(doc, "Read the concept explanation until you can say it in your own words.")
    H.numbered(doc, "Read the file blocks: which file owns the idea.")
    H.numbered(doc, "Study methods + parameters + call chain.")
    H.numbered(doc, "Note libraries and why they were chosen.")
    H.numbered(doc, "Only then open the file in the IDE to see the real code.")
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "1. Application startup & FastAPI application object", 1)
    concept_block(
        doc,
        "1.1 Concept: Application factory / ASGI app",
        meaning="A factory function builds the web application object that the server runs.",
        why="Keeps configuration (middleware, routers, error handlers) in one place and makes testing easier.",
        how_works="The ASGI server imports a callable/app object, runs lifespan startup/shutdown, and dispatches HTTP requests to routes.",
        in_project="create_app() builds FastAPI, registers CORS, exception handlers, routers, and /easy. Module-level app = create_app() is what uvicorn loads.",
        related="Uvicorn, lifespan, middleware, routers",
    )
    file_block(
        doc,
        "api/main.py",
        purpose="Create and configure the FastAPI application; mount routers and global error handling.",
        libraries=[
            ("fastapi.FastAPI", "Web framework application object, routing, OpenAPI"),
            ("fastapi.middleware.cors.CORSMiddleware", "Allow browser cross-origin calls during demos"),
            ("fastapi.responses.FileResponse", "Serve easy.html"),
            ("contextlib.asynccontextmanager", "Lifespan startup/shutdown hook"),
            ("config.env_loader.load_dotenv", "Ensure .env is loaded when API starts"),
            ("utils.logger.get_logger", "Log startup and unhandled errors"),
        ],
        methods=[
            {
                "name": "lifespan(_app)",
                "resp": "Runs once at startup (load dotenv, log) and ends on shutdown.",
                "params": "_app: FastAPI instance (unused beyond framework contract)",
                "returns": "async context manager (yield)",
                "calls": "load_dotenv(); logger.info",
            },
            {
                "name": "create_app()",
                "resp": "Construct FastAPI with tags, middleware, handlers, routers; return application.",
                "params": "none",
                "returns": "FastAPI application",
                "calls": "include_router for auth/journalist/aia/cae/publisher/editor/manager/admin; add_middleware; exception handlers",
            },
            {
                "name": "easy_tester()",
                "resp": "HTTP GET /easy returns the static HTML tester.",
                "params": "none (route handler)",
                "returns": "FileResponse(api/static/easy.html)",
                "calls": "FileResponse",
            },
        ],
        calls="All api.routers.*; auth/http error types; load_dotenv",
        called_by="uvicorn api.main:app; pytest TestClient(app)",
    )
    file_block(
        doc,
        "requirements.txt / run command",
        purpose="Declare uvicorn and tell operators how to boot the API.",
        libraries=[("uvicorn[standard]", "ASGI server that loads api.main:app and serves HTTP")],
        methods=[],
        calls="Imports api.main:app",
        called_by="Developer shell: uvicorn api.main:app --reload",
    )
    flow(
        doc,
        "Startup call chain",
        [
            "Shell starts uvicorn with target api.main:app",
            "Python imports api.main → create_app() runs → routers registered",
            "Lifespan startup calls load_dotenv()",
            "Server accepts HTTP; each request hits a router function",
        ],
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "2. Configuration & environment loading", 1)
    concept_block(
        doc,
        "2.1 Concept: Externalized configuration",
        meaning="Settings (DB host, secrets, batch sizes) live outside source code, usually in environment variables / .env files.",
        why="The same code can run on different machines without editing Python files; secrets stay out of git.",
        how_works="Process environment is a key→value map. At startup, a loader reads .env into that map if keys are not already set.",
        in_project="config/env_loader.py parses .env; db_config/runtime/constants read os.environ.",
        related="12-factor app idea, secrets management",
    )
    file_block(
        doc,
        "config/env_loader.py",
        purpose="Load project .env into os.environ once.",
        libraries=[
            ("os", "Write environment keys"),
            ("pathlib.Path", "Locate project-root .env"),
        ],
        methods=[
            {
                "name": "load_dotenv(path=None)",
                "resp": "Parse KEY=VALUE lines; set missing keys in os.environ; skip comments/blanks.",
                "params": "path: optional Path; default ROOT/.env",
                "returns": "Path loaded or None if missing",
                "calls": "Path.read_text; os.environ assignment",
                "notes": "Does not override keys already present in the environment.",
            }
        ],
        calls="Filesystem .env",
        called_by="api lifespan, db_config, runtime, constants, app.py",
    )
    file_block(
        doc,
        "config/db_config.py",
        purpose="Build immutable DatabaseConfig for Postgres connections.",
        libraries=[
            ("dataclasses.dataclass", "Frozen config object"),
            ("os.environ", "Read NEWSROOM_DB_*"),
            ("config.runtime", "sslmode + connect timeout helpers"),
        ],
        methods=[
            {
                "name": "DatabaseConfig.dsn_kwargs()",
                "resp": "Dict of kwargs suitable for psycopg2.connect.",
                "params": "self",
                "returns": "dict with host/port/dbname/user/password/ssl/keepalives",
            },
            {
                "name": "load_db_config()",
                "resp": "Read env and return DatabaseConfig.",
                "params": "none",
                "returns": "DatabaseConfig",
                "calls": "load_dotenv(); db_connect_timeout(); db_sslmode()",
            },
        ],
        calls="env_loader, runtime",
        called_by="database/connection.py",
    )
    file_block(
        doc,
        "config/runtime.py",
        purpose="Pipeline/IO tunables from env with safe defaults and clamping.",
        libraries=[("os", "Read NEWSROOM_CSV_CHUNK_ROWS and related flags")],
        methods=[
            {"name": "csv_chunk_rows()", "resp": "Pandas chunk size (min 500).", "params": "none", "returns": "int"},
            {"name": "db_insert_batch()", "resp": "Bulk insert batch size (min 50).", "params": "none", "returns": "int"},
            {"name": "pipeline_file_by_file()", "resp": "Whether multi-file ETL runs per CSV.", "params": "none", "returns": "bool"},
            {"name": "write_processed_files()", "resp": "Whether to write data/processed snapshots.", "params": "none", "returns": "bool"},
        ],
        calls="load_dotenv via helpers",
        called_by="ingestion_service, cleaners orchestrator, admin pipeline",
    )
    file_block(
        doc,
        "config/constants.py",
        purpose="Stable business vocabulary: roles, capabilities, platforms, password/JWT policy helpers, demo passwords.",
        libraries=[("os", "Read NEWSROOM_JWT_SECRET"), ("config.env_loader", "Ensure env loaded before reading secret")],
        methods=[
            {
                "name": "get_jwt_secret()",
                "resp": "Return JWT signing secret or raise RuntimeError if unset.",
                "params": "none",
                "returns": "str secret",
                "notes": "No hardcoded fallback secret in code.",
            }
        ],
        calls="load_dotenv",
        called_by="security.py, permission maps across app, schemas/rules, services",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "3. Password hashing (PBKDF2)", 1)
    concept_block(
        doc,
        "3.1 Concept: Password hashing",
        meaning="Transform a password into a stored digest that is hard to reverse. Verification re-hashes the attempt and compares.",
        why="If the database leaks, attackers should not get usable passwords easily.",
        how_works="PBKDF2 applies a pseudorandom function many times with a salt. Salt prevents rainbow tables. Constant-time compare avoids timing leaks.",
        in_project="hash_password stores salt_hex$digest_hex in users.password_hash; verify_password checks logins and password changes.",
        related="Authentication, JWT issuance only after verify succeeds",
    )
    file_block(
        doc,
        "modules/authentication/security.py (password part)",
        purpose="Hash and verify passwords; also JWT helpers (next chapter).",
        libraries=[
            ("hashlib.pbkdf2_hmac", "Core PBKDF2-HMAC-SHA256"),
            ("hmac.compare_digest", "Timing-safe equality"),
            ("os.urandom", "Random salt bytes"),
            ("config.constants", "PASSWORD_HASH_ITERATIONS, PASSWORD_SALT_BYTES"),
        ],
        methods=[
            {
                "name": "hash_password(password, salt=None)",
                "resp": "Create stored hash string.",
                "params": "password: str; salt: optional bytes (reuse when verifying)",
                "returns": "str 'salt_hex$digest_hex'",
                "calls": "os.urandom or given salt; hashlib.pbkdf2_hmac",
            },
            {
                "name": "verify_password(password, password_hash)",
                "resp": "True if password matches stored hash.",
                "params": "password: attempt; password_hash: DB value",
                "returns": "bool",
                "calls": "hash_password with extracted salt; compare_digest",
                "notes": "Malformed hashes return False (fail closed).",
            },
        ],
        calls="constants for iteration counts",
        called_by="auth_service.authenticate/change_password/admin_reset; UserService user creation",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "4. JWT authentication", 1)
    concept_block(
        doc,
        "4.1 Concept: JWT",
        meaning="JSON Web Token: header.payload.signature. Payload holds claims; signature proves the server issued it and it was not altered.",
        why="APIs need a portable proof of login. JWT can be verified with a secret without looking up a random opaque id in a session table.",
        how_works="Server signs claims with HS256 secret. Client sends Bearer token. Server verifies signature + exp, then trusts user_id claim enough to load the live user from DB.",
        in_project="Login returns JWT as session_token. resolve_session decodes JWT, checks jti denylist, loads user. Logout adds jti to denylist.",
        related="Bearer scheme, RBAC after identity, PBKDF2 before issue",
    )
    concept_block(
        doc,
        "4.2 Concept: HS256 & jti denylist",
        meaning="HS256 = HMAC-SHA256 with a shared secret. jti = unique token id. A denylist remembers revoked jtis until expiry.",
        why="Symmetric crypto is simple for one backend. Logout must invalidate tokens that would otherwise stay valid until exp.",
        how_works="On logout, store jti→exp. On resolve, reject if jti is listed and not yet expired.",
        in_project="_REVOKED_JTI dict in auth_service (process-local).",
        related="JWT, Bearer",
    )
    file_block(
        doc,
        "modules/authentication/security.py (JWT part)",
        purpose="Create and decode access tokens.",
        libraries=[
            ("PyJWT (import jwt)", "jwt.encode / jwt.decode for HS256 tokens"),
            ("secrets.token_urlsafe", "Random jti values"),
            ("datetime", "iat/exp timestamps"),
            ("get_jwt_secret()", "Required secret from env"),
        ],
        methods=[
            {
                "name": "create_access_token(*, user_id, username, role_code='')",
                "resp": "Build claims and return signed JWT string.",
                "params": "user_id: int; username: str; role_code: str optional",
                "returns": "str JWT",
                "calls": "get_jwt_secret(); jwt.encode; secrets.token_urlsafe for jti",
            },
            {
                "name": "decode_access_token(token)",
                "resp": "Verify signature/claims; return payload dict.",
                "params": "token: str JWT",
                "returns": "dict claims",
                "calls": "jwt.decode with require exp,sub,jti",
                "notes": "Raises jwt.PyJWTError subclasses on failure.",
            },
        ],
        calls="config.constants get_jwt_secret, JWT_ALGORITHM, SESSION_TTL_HOURS",
        called_by="auth_service.authenticate / resolve_session / logout",
    )
    file_block(
        doc,
        "modules/authentication/auth_service.py",
        purpose="Login orchestration, JWT resolve, logout revoke, password change/reset, CLI token file.",
        libraries=[
            ("PyJWT errors", "Catch ExpiredSignatureError / PyJWTError"),
            ("UserDAO", "Load/update users"),
            ("UserRepository", "Desk profile ids in payload"),
            ("security.*", "hash/verify/create/decode"),
            ("capabilities_for_role", "Attach capabilities to payload"),
            ("json/pathlib helpers", "CLI logs/.session_token"),
        ],
        methods=[
            {
                "name": "authenticate(username, password, *, ip_address=None, user_agent=None)",
                "resp": "Validate credentials; issue JWT; save CLI file; return user payload + session_token.",
                "params": "username/password required; ip/ua reserved unused",
                "returns": "dict including session_token (JWT) and capabilities",
                "calls": "UserDAO.read_by_username; verify_password; record_login_success; create_access_token; _save_cli_token; _user_payload",
            },
            {
                "name": "resolve_session(session_token=None)",
                "resp": "Verify JWT (or CLI stored JWT); reject revoked jti; load active user; return payload.",
                "params": "session_token optional str; if empty uses CLI file",
                "returns": "user dict with capabilities/profiles",
                "calls": "decode_access_token; _is_revoked; UserDAO.read_by_id; _user_payload",
            },
            {
                "name": "logout(session_token=None)",
                "resp": "Revoke JWT jti and/or clear CLI file.",
                "params": "optional token string",
                "returns": "None",
                "calls": "decode_access_token; _revoke_jti; _clear_cli_token",
            },
            {
                "name": "change_password(user_id, current_password, new_password)",
                "resp": "Verify current; validate new; update hash.",
                "params": "user_id int; current/new password strings",
                "returns": "None",
                "calls": "require_password; verify_password; hash_password; UserDAO.update_password_hash",
            },
        ],
        calls="security, UserDAO, UserRepository, permission_service.capabilities_for_role, validators",
        called_by="api/routers/auth.py, api/deps.py, services/access.py, app.py console",
    )
    file_block(
        doc,
        "api/deps.py",
        purpose="FastAPI dependencies that extract Bearer JWT and resolve the current user.",
        libraries=[
            ("fastapi.Depends", "Dependency injection"),
            ("fastapi.security.HTTPBearer", "Parse Authorization header"),
            ("fastapi.HTTPException", "401 when missing/invalid"),
        ],
        methods=[
            {
                "name": "get_session_token(creds=Depends(bearer_scheme))",
                "resp": "Return raw JWT string from Bearer header.",
                "params": "creds: HTTPAuthorizationCredentials | None",
                "returns": "str token",
                "notes": "auto_error=False so custom 401 message is used",
            },
            {
                "name": "get_current_user(token=Depends(get_session_token))",
                "resp": "Resolve JWT to user payload.",
                "params": "token str",
                "returns": "dict user",
                "calls": "resolve_session(token)",
            },
        ],
        calls="auth_service.resolve_session",
        called_by="Most protected routers via Depends(get_session_token) or get_current_user",
    )
    flow(
        doc,
        "Login → API call → logout chain",
        [
            "POST /auth/login → authenticate → verify_password → create_access_token → JSON session_token",
            "Client stores JWT; sends Authorization: Bearer <JWT>",
            "Route Depends(get_session_token) → require_capability_session or get_current_user → resolve_session → decode_access_token → UserDAO",
            "POST /auth/logout → logout(token) → revoke jti",
        ],
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "5. RBAC & capabilities", 1)
    concept_block(
        doc,
        "5.1 Concept: RBAC + capabilities",
        meaning="Users have a role. Each role grants a set of capability strings (actions).",
        why="Newsroom desks need different powers without writing if role==X in every function.",
        how_works="After identity is known, check whether role_code includes required capability. Admin short-circuits to allow all.",
        in_project="ROLE_CAPABILITIES map in constants; permission_service helpers; access.require_capability_session combines JWT resolve + capability check.",
        related="JWT identity, desk profiles",
    )
    file_block(
        doc,
        "services/permission_service.py",
        purpose="Pure RBAC helpers with no HTTP knowledge.",
        libraries=[("config.constants", "ROLE_ADMIN, ROLE_CAPABILITIES")],
        methods=[
            {"name": "capabilities_for_role(role_code)", "resp": "Tuple of capabilities.", "params": "role_code str", "returns": "tuple[str,...]"},
            {"name": "has_capability(role_code, capability)", "resp": "True if allowed (admin always True).", "params": "role_code, capability", "returns": "bool"},
            {"name": "require_capability(role_code, capability)", "resp": "Raise PermissionError if missing.", "params": "role_code, capability", "returns": "None"},
        ],
        calls="constants map only",
        called_by="access.py, auth_service._user_payload, app.py menu gating",
    )
    file_block(
        doc,
        "services/access.py",
        purpose="One gate used by modules/routers: resolve token then require capability.",
        libraries=[("auth_service", "resolve_session"), ("permission_service", "require_capability"), ("utils.errors", "AuthError/PermissionDeniedError")],
        methods=[
            {
                "name": "require_capability_session(capability, session_token=None)",
                "resp": "Return user dict if JWT valid and capability granted.",
                "params": "capability: str key; session_token: optional JWT",
                "returns": "dict user payload",
                "calls": "resolve_session; require_capability",
            }
        ],
        calls="auth_service, permission_service",
        called_by="JournalistModule, AdminModule, UserService, most desk routers",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "6. Database connection, DAO, repository, entity", 1)
    concept_block(
        doc,
        "6.1 Concept: Entity / DAO / Repository",
        meaning="Entity = in-memory row shape. DAO = SQL for one table. Repository = multi-table business save/load.",
        why="Keeps routers free of SQL and keeps multi-table writes consistent (content + news).",
        how_works="Service builds Entity → Repository/DAO executes SQL via db_cursor → Postgres stores rows → dict rows return upward.",
        in_project="entities/*, dao/*, repository/*, database/connection.py",
        related="psycopg2, RealDictCursor",
    )
    file_block(
        doc,
        "database/connection.py",
        purpose="Connect to Postgres; provide cursor context; apply SQL; init schema.",
        libraries=[
            ("psycopg2", "PostgreSQL driver"),
            ("psycopg2.extras.RealDictCursor", "Dict-like rows"),
            ("config.db_config", "DSN kwargs"),
        ],
        methods=[
            {"name": "get_connection(cfg=None)", "resp": "Open raw connection.", "params": "optional DatabaseConfig", "returns": "psycopg2 connection", "calls": "psycopg2.connect(**dsn_kwargs)"},
            {"name": "db_cursor(cfg=None)", "resp": "Context manager yielding RealDictCursor; commits; closes.", "params": "optional config", "returns": "generator cursor"},
            {"name": "apply_sql_file(path)", "resp": "Execute SQL file statements.", "params": "Path to .sql", "returns": "None"},
            {"name": "init_schema()", "resp": "Apply newsmind.sql then seed demo users.", "params": "none", "calls": "apply_sql_file; seed_demo_users"},
        ],
        calls="db_config, seed_demo_users",
        called_by="All DAOs via BaseDAO; app.py --init-db",
    )
    file_block(
        doc,
        "dao/base_dao.py",
        purpose="Shared execute/get/delete/list for table DAOs.",
        libraries=[("database.connection.db_cursor", "DB access")],
        methods=[
            {
                "name": "execute(sql, params=None, fetch='none')",
                "resp": "Run SQL; optionally fetch one/all or return rowcount.",
                "params": "sql str; params sequence; fetch mode",
                "returns": "row / list / rowcount",
            },
            {"name": "get_by_id(pk_name, pk_value)", "resp": "SELECT * by PK.", "params": "column name + int id", "returns": "dict|None"},
            {"name": "delete_by_id(pk_name, pk_value)", "resp": "DELETE by PK.", "params": "column + id", "returns": "int rowcount"},
            {"name": "list_all(limit=500)", "resp": "Recent rows limited.", "params": "limit int", "returns": "list[dict]"},
        ],
        calls="db_cursor",
        called_by="All concrete DAO subclasses",
    )
    file_block(
        doc,
        "repository/content_repository.py",
        purpose="Aggregate content-domain writes/reads across DAOs.",
        libraries=[("dao.*", "content/article/news/evidence/pitch/raw"), ("entities.content.*", "dataclass payloads")],
        methods=[
            {"name": "save_pitch(pitch)", "resp": "Insert story pitch.", "params": "StoryPitch entity", "returns": "int id", "calls": "StoryPitchDAO.create"},
            {
                "name": "save_content_bundle(content, *, event_location='')",
                "resp": "Insert content then news or article child based on content_kind.",
                "params": "Content entity; optional event_location",
                "returns": "content_id",
                "calls": "ContentDAO.create; NewsDAO.create or ArticleDAO.create",
            },
            {"name": "save_evidence(evidence)", "resp": "Insert evidence.", "params": "Evidence entity", "returns": "id", "calls": "EvidenceDAO.create"},
            {"name": "get_content(content_id)", "resp": "Require content row.", "params": "int id", "returns": "dict", "calls": "ContentDAO.require"},
        ],
        calls="multiple DAOs",
        called_by="ContentService, PersistenceService, AIA pitch paths",
    )
    H.note(doc, "Individual table DAOs (content_dao, user_dao, adaptation_dao, …) follow the same pattern: create/read/update using entities or kwargs and BaseDAO.execute.")
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "7. HTTP schemas, validation, errors", 1)
    concept_block(
        doc,
        "7.1 Concept: Boundary validation vs domain validation",
        meaning="Boundary validation checks HTTP shapes early. Domain validation enforces business rules inside services/cleaners.",
        why="Bad JSON should fail before DB work; CLI/ETL also need rules without HTTP.",
        how_works="Pydantic parses request bodies. utils.validators raise ValidationError. API maps errors to HTTP statuses.",
        in_project="api/schemas/* + rules.py; utils/validators.py; utils/errors.py; api/http_errors.py",
        related="FastAPI 422 handler",
    )
    file_block(
        doc,
        "api/schemas/rules.py",
        purpose="Shared Annotated types (username, strong password, title/body lengths, enums).",
        libraries=[("pydantic", "StringConstraints, AfterValidator, Field"), ("utils.validators / constants", "Business allowed sets")],
        methods=[],
        calls="constants MIN_TITLE_LENGTH etc.; require_password",
        called_by="All api/schemas/* modules",
    )
    file_block(
        doc,
        "utils/validators.py",
        purpose="require_* helpers and validate_content_record used by services and cleaners.",
        libraries=[("re", "Email regex"), ("config.constants", "Allowed statuses/kinds"), ("utils.errors.ValidationError", "Failure type")],
        methods=[
            {"name": "require_title / require_body / require_password / require_content_status / …", "resp": "Normalize and validate a field or raise ValidationError.", "params": "raw value (+ label where needed)", "returns": "cleaned str/number"},
            {"name": "validate_content_record(record)", "resp": "Return list of error strings for a content-like dict.", "params": "mapping with title/text/status", "returns": "list[str]"},
        ],
        calls="constants",
        called_by="ContentService, cleaners SchemaCleaner, auth password paths, DAOs sometimes",
    )
    file_block(
        doc,
        "api/http_errors.py",
        purpose="Translate domain exceptions into HTTPException statuses.",
        libraries=[("fastapi.HTTPException", "Raise HTTP errors"), ("utils.errors", "AppError hierarchy")],
        methods=[
            {
                "name": "raise_http_error(exc)",
                "resp": "Always raises HTTPException mapped from exception type.",
                "params": "exc: Exception",
                "returns": "never returns",
                "notes": "Auth→401, Permission→403, NotFound→404, missing model→503, Validation→400, else 500",
            }
        ],
        calls="logger on unknown errors",
        called_by="Routers' except blocks; AppError handler in main.py",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "8. Journalist desk (module → service → DB)", 1)
    concept_block(
        doc,
        "8.1 Concept: Journalist façade + content authorship",
        meaning="A façade checks journalist_tools capability then delegates to content/AI helper services. Authorship uses journalist_id, not user_id.",
        why="HTTP routers stay thin; FK integrity requires desk profile id.",
        how_works="JournalistModule._user() gates access; _author_id() reads profiles or ensure_for_user; then ContentService creates content+child+evidence.",
        in_project="modules/journalist + services/content + services/journalist + api/routers/journalist.py",
        related="Evidence, credibility, relevancy",
    )
    file_block(
        doc,
        "modules/journalist/journalist_module.py",
        purpose="Capability-gated journalist tools and desk CRUD façade.",
        libraries=[("services.access", "require_capability_session"), ("ContentService", "CRUD"), ("services.journalist helpers", "duplicates/validate/credibility"), ("JournalistDAO", "ensure profile")],
        methods=[
            {"name": "__init__(session_token=None, content=None)", "resp": "Store token and content service.", "params": "optional token + ContentService", "returns": "instance"},
            {"name": "_user()", "resp": "Require CAP_JOURNALIST_TOOLS.", "params": "none", "returns": "user dict", "calls": "require_capability_session"},
            {"name": "_author_id(user)", "resp": "Resolve journalist_id for content.author_id.", "params": "user dict", "returns": "int|None", "calls": "profiles or JournalistDAO.ensure_for_user"},
            {"name": "add_news(**kwargs) / add_article(**kwargs)", "resp": "Create desk items with author_id defaulted.", "params": "title/body/evidence/…", "returns": "dict with actor + ids", "calls": "ContentService.add_news/add_article"},
            {"name": "credibility(content_id, *, limit=5)", "resp": "Assess claims vs attached evidence.", "params": "content_id int; limit", "returns": "report dict", "calls": "get_content; list_evidence; assess_credibility"},
            {"name": "related_content(title, text, *, limit=8)", "resp": "TF-IDF related published docs.", "params": "title/text/limit", "returns": "matches + scores", "calls": "ml.knowledge.score_content_relevancy"},
        ],
        calls="access, ContentService, journalist services, ml.knowledge, JournalistDAO",
        called_by="api/routers/journalist.py via JournalistModule(session_token=token)",
    )
    file_block(
        doc,
        "services/content/content_service.py",
        purpose="Validated create/list/update for categories, pitches, news, articles, evidence.",
        libraries=[("entities.content.*", "Payloads"), ("ContentRepository/CategoryDAO", "Persistence"), ("utils.validators", "require_*")],
        methods=[
            {
                "name": "add_news(...)",
                "resp": "Validate; require ≥1 evidence; insert content(kind=news)+news+evidence.",
                "params": "title, body, summary, event_*, severity, breaking, status, author_id, evidence list",
                "returns": "dict ids",
                "calls": "validate_content_record; repo.content.create; repo.news.create; add_evidence loop",
            },
            {
                "name": "add_article(...)",
                "resp": "Same pattern for articles.",
                "params": "title, body, article_type, read_time, status, author_id, evidence",
                "returns": "dict ids",
            },
            {"name": "update_content_status(content_id, status)", "resp": "Validate status and update.", "params": "id + status str", "returns": "updated info", "calls": "require_content_status; ContentDAO.update_status"},
        ],
        calls="repository, validators, CategoryDAO",
        called_by="JournalistModule, ContentModule, AdminModule raw lists, some seeds",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "9. ETL: ingest → clean → persist", 1)
    concept_block(
        doc,
        "9.1 Concept: ETL pipeline",
        meaning="Extract data from files, transform/clean it, load into the system of record.",
        why="External CSVs are messy; the desk model needs clean rows.",
        how_works="Ingest reads/normalizes CSV and may stage raw rows; cleaners reject/fix; persistence writes content/pitches and reports.",
        in_project="AdminModule orchestrates IngestionService + CleaningOrchestrator + PersistenceService + ReportService.",
        related="Hash skip, chunked reads, cleaner stages",
    )
    file_block(
        doc,
        "services/ingestion_service.py",
        purpose="Discover CSVs, hash them, chunk-read, normalize rows, ingest pitches.",
        libraries=[
            ("pandas", "read_csv chunksize"),
            ("hashlib.md5", "File fingerprint for change detection"),
            ("utils.csv_fields.normalize_row", "Header alias mapping"),
            ("IngestFileDAO", "Persist hashes"),
            ("config.runtime", "chunk size / warn threshold"),
        ],
        methods=[
            {"name": "list_csv_files()", "resp": "Relative paths under data/raw.", "params": "none", "returns": "list[str]"},
            {"name": "resolve_csv(source_file)", "resp": "Safe path under raw dir or raise.", "params": "relative csv path", "returns": "Path"},
            {"name": "file_needs_ingest(source_file)", "resp": "True if new or hash changed.", "params": "path str", "returns": "bool", "calls": "get_by_source; _file_hash"},
            {"name": "load_one_csv(source_file, *, register=True)", "resp": "Read usable rows; optionally upsert hash.", "params": "file; register flag", "returns": "dict records/collections/hash stats"},
            {"name": "ingest_all_content(*, only_new=False)", "resp": "Load all or only changed files.", "params": "only_new bool", "returns": "combined records payload"},
        ],
        calls="pandas, IngestFileDAO, csv_fields, progress logger",
        called_by="AdminModule.ingest / ingest_file / pipeline",
    )
    file_block(
        doc,
        "cleaners/orchestrator.py + pipeline.py + stages/*",
        purpose="Transform record lists through ordered cleaners; optional processed file output.",
        libraries=[("pandas optional writes", "processed snapshots"), ("utils.helpers/validators", "normalize keys / schema checks"), ("config.constants", "allowed enums")],
        methods=[
            {"name": "CleaningOrchestrator.clean_content(records)", "resp": "Run content pipeline; return kept/rejected/stats/report paths.", "params": "list[dict]", "returns": "result dict", "calls": "CleaningPipeline.run"},
            {"name": "CleaningPipeline.run(records)", "resp": "Apply each BaseCleaner sequentially.", "params": "records", "returns": "CleanerResult aggregate"},
            {"name": "TextCleaner / NullCleaner / DuplicateCleaner / SchemaCleaner.clean", "resp": "Stage-specific keep/reject.", "params": "records list", "returns": "CleanerResult"},
        ],
        calls="stage cleaners, QualityReport",
        called_by="AdminModule.clean / pipeline; also ML dataset push cleaning",
    )
    file_block(
        doc,
        "services/persistence_service.py",
        purpose="Write raw staging and cleaned domain rows to Postgres.",
        libraries=[("entities", "Content/News/Article/Evidence/StoryPitch"), ("ContentRepository/UserRepository", "Saves"), ("validators", "status/title checks")],
        methods=[
            {"name": "persist_raw_records(records, *, cleaning_status='pending')", "resp": "Bulk insert raw_ingest.", "params": "list dicts + status", "returns": "list ids"},
            {"name": "persist_content(records)", "resp": "Save kept content bundles (+ evidence when present).", "params": "cleaned rows", "returns": "counts/ids"},
            {"name": "persist_rejected(records)", "resp": "Store rejects in raw_ingest.", "params": "rejected rows", "returns": "count"},
            {"name": "persist_pitches(records)", "resp": "Save story pitches.", "params": "pitch rows", "returns": "count"},
        ],
        calls="repositories/DAOs",
        called_by="AdminModule.persist / pipeline",
    )
    file_block(
        doc,
        "modules/admin/admin_module.py",
        purpose="Capability-gated ETL façade used by admin API and console.",
        libraries=[("IngestionService", "extract"), ("CleaningOrchestrator", "transform"), ("PersistenceService/ReportService", "load + reports"), ("access", "caps")],
        methods=[
            {"name": "ingest / ingest_file / clean / persist / run_pipeline / ingest_and_clean", "resp": "Orchestrate ETL steps with progress messages.", "params": "only_new / source_file as relevant", "returns": "result dict with actor/stats", "calls": "underlying services"},
        ],
        calls="ingestion, cleaners, persistence, report, ContentService for raw list",
        called_by="api/routers/admin.py, app.py menus/flags",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "10. Desk services: editor, manager, publisher, AIA, CAE", 1)

    concept_block(
        doc,
        "10.1 Editor queue urgency (trained model concept)",
        meaning="A supervised classifier predicts how urgently editors should review an item.",
        why="Submitted queues need prioritization, not only chronological order.",
        how_works="Offline: labeled headlines → TF-IDF + features → XGBoost → joblib artifact. Online: load artifact, predict label, map to urgent/high/medium/low.",
        in_project="ml/editor/queue_urgency.py used by EditorService.review_queue / score endpoint.",
        related="TF-IDF, model artifact, fallback",
    )
    file_block(
        doc,
        "ml/editor/queue_urgency.py",
        purpose="Load urgency model; predict desk urgency.",
        libraries=[("joblib", "Load model bundle"), ("numpy/scipy.sparse", "Feature matrices"), ("functools.lru_cache", "Load once per process")],
        methods=[
            {"name": "_load_model()", "resp": "Cached load of model.joblib or None.", "params": "none", "returns": "bundle dict|None"},
            {"name": "predict_editor_queue_urgency(headline, body='')", "resp": "Return urgency, confidence, probabilities, source.", "params": "headline/body strings", "returns": "dict", "notes": "source=model or fallback"},
            {"name": "model_available()", "resp": "Whether artifact exists/loads.", "params": "none", "returns": "bool"},
        ],
        calls="joblib file under artifacts/models/editor_queue_urgency/",
        called_by="services/editor/editor_service.py; api/routers/editor.py score",
    )
    file_block(
        doc,
        "services/editor/editor_service.py",
        purpose="Pitch/content queues, approve/reject/rework/assign, duplicates, journalist suggestions, urgency scoring.",
        libraries=[("StoryPitchDAO/ContentDAO", "Data"), ("ml.editor", "urgency"), ("ml.common", "similarity for pitch duplicates"), ("db_cursor", "ad-hoc SQL")],
        methods=[
            {"name": "score_editor_queue_urgency(title, summary='')", "resp": "Wrap ML predict.", "params": "title/summary", "returns": "urgency dict"},
            {"name": "review_queue(pitch_status, content_status)", "resp": "Merge tasks ordered by urgency.", "params": "status filters", "returns": "queue payload"},
            {"name": "approve_pitch / reject_pitch / approve_content / reject_content / send_content_rework / assign_content", "resp": "State transitions + optional remarks/assignee.", "params": "ids + remarks/assignee_user_id/note", "returns": "updated dicts"},
        ],
        calls="DAOs, ml.editor, ml.common",
        called_by="api/routers/editor.py; ManagerService delegation",
    )

    concept_block(
        doc,
        "10.2 Manager analytics concept",
        meaning="Operational metrics over the pipeline (bottlenecks, workload, deadline risk, resources).",
        why="Managers need system-wide visibility beyond single-item review.",
        how_works="SQL aggregates + reuse of editor review methods.",
        in_project="services/manager/manager_service.py + api/routers/manager.py",
        related="Editor service composition",
    )
    file_block(
        doc,
        "services/manager/manager_service.py",
        purpose="Compose EditorService for review; add overview/analytics methods.",
        libraries=[("EditorService", "Delegation"), ("PublicationDAO + db_cursor", "Aggregates")],
        methods=[
            {"name": "overview / bottlenecks / business_analytics / workload / deadline_risk / resources", "resp": "Return analytics structures for manager UI/API.", "params": "deadline_risk takes submitted_hours/rework_hours thresholds", "returns": "dict payloads"},
            {"name": "approve_* / list_* / review_queue / assign_content", "resp": "Delegate to EditorService.", "params": "same as editor", "returns": "same as editor"},
        ],
        calls="EditorService, DAOs, SQL",
        called_by="api/routers/manager.py",
    )

    concept_block(
        doc,
        "10.3 Publisher / publication concept",
        meaning="Approved content enters a publication record that can be templated, previewed, scheduled, or published.",
        why="Separate editorial approval from release mechanics.",
        how_works="ensure publication row → assign template → publish sets content status published and timestamps.",
        in_project="PublisherService + publication table/DAO + publisher router",
        related="Content lifecycle",
    )
    file_block(
        doc,
        "services/publisher/publisher_service.py",
        purpose="Publication queue operations.",
        libraries=[("PublicationDAO/ContentDAO", "Persistence"), ("PUBLICATION_TEMPLATES constants", "Template catalog"), ("utils.errors", "NotFound/Validation")],
        methods=[
            {"name": "list_articles / templates / approve / assign_template / preview / publish / schedule / analytics", "resp": "Full publisher lifecycle.", "params": "content_id; template_code; scheduled_at datetime as needed", "returns": "dicts with publication info"},
        ],
        calls="DAOs, constants",
        called_by="api/routers/publisher.py",
    )

    concept_block(
        doc,
        "10.4 AIA heuristics concept",
        meaning="Engagement/interest/trend scores from formulas and keyword cues—not trained artifacts.",
        why="Provide analyst tooling without requiring a telemetry ML model.",
        how_works="Weighted combinations of views/likes/shares/comments; trend regex on text; pitches stored with scores.",
        in_project="ml/aia/audience_scores.py → AIAService → /aia routes",
        related="Story pitch",
    )
    file_block(
        doc,
        "ml/aia/audience_scores.py",
        purpose="Pure functions for engagement, interest, trend.",
        libraries=[("re", "Trend keyword patterns")],
        methods=[
            {"name": "predict_engagement(*, views, likes, shares, comments)", "resp": "Score dict source=heuristic.", "params": "non-negative floats", "returns": "dict"},
            {"name": "predict_interest(...)", "resp": "Interest from interaction intensity.", "params": "metrics (+ optional engagement_raw)", "returns": "dict"},
            {"name": "predict_trend(headline='', body='')", "resp": "Trend score from text cues.", "params": "strings", "returns": "dict"},
        ],
        calls="none external",
        called_by="services/aia/aia_service.py",
    )
    file_block(
        doc,
        "services/aia/aia_service.py",
        purpose="Wrap heuristics; create/list pitches; performance analytics loop.",
        libraries=[("ml.aia", "predict_*"), ("ContentRepository/StoryPitch", "Persist pitches"), ("db_cursor", "Analytics SQL")],
        methods=[
            {"name": "analyze_engagement/interest/trends", "resp": "Proxy to ml.aia.", "params": "metrics or title/summary", "returns": "score dicts"},
            {"name": "generate_story_pitch(payload)", "resp": "Compute scores, set priority, save StoryPitch AI_GENERATED.", "params": "schema-like payload", "returns": "pitch response"},
            {"name": "performance_analytics()", "resp": "Publication→AIA loop stats.", "params": "none", "returns": "analytics dict"},
        ],
        calls="ml.aia, repository, SQL",
        called_by="api/routers/aia.py",
    )

    concept_block(
        doc,
        "10.5 CAE extractive adaptation concept",
        meaning="Choose which sentences to keep for a target platform, then format output; humans review drafts.",
        why="Channel constraints differ; avoid paid generative APIs for core demo path.",
        how_works="Trained sentence keep/drop model + platform limits → drafts in DB → approve/reject/regenerate/finalize.",
        in_project="ml/adaptation/* + AdaptationService/ReviewService + /cae routes + adaptation_* tables",
        related="Model artifact, platforms constants",
    )
    file_block(
        doc,
        "ml/adaptation/predict.py (+ model_loader, platforms, validate)",
        purpose="Inference: score sentences, apply thresholds/limits, format and fact-check flags.",
        libraries=[("joblib via model_loader", "Load CAE artifact"), ("PLATFORM_SENTENCE_LIMITS", "Caps per platform"), ("split_sentences", "Sentence segmentation")],
        methods=[
            {
                "name": "predict_sentences(title, content, platform, threshold_delta=0, sentence_delta=0, prioritize_quotes=False, prioritize_numbers=False)",
                "resp": "Return selected sentences with scores + meta + threshold used.",
                "params": "title/content/platform + tuning flags used during regenerate",
                "returns": "tuple(selected, meta, threshold)",
                "calls": "load_model; split_sentences; model.predict_proba path inside",
            }
        ],
        calls="model_loader, sentences, constants",
        called_by="AdaptationService.create; ReviewService.regenerate",
    )
    file_block(
        doc,
        "services/adaptation/adaptation_service.py & review_service.py",
        purpose="Create adaptation requests/drafts; human review actions.",
        libraries=[("AdaptationDAO", "DB"), ("ml.adaptation.predict/format/validate", "Generation"), ("constants platforms", "Validation of targets")],
        methods=[
            {"name": "AdaptationService.create(original_title, original_content, target_platforms, created_by)", "resp": "Insert request; generate draft per platform.", "params": "strings + platform list + user id", "returns": "request+drafts dict"},
            {"name": "AdaptationService.get_request(request_id)", "resp": "Load request with drafts.", "params": "id", "returns": "dict"},
            {"name": "ReviewService.approve/reject/regenerate/finalize/versions", "resp": "Review workflow on a draft id.", "params": "draft_id, user_id, remarks/final fields as required", "returns": "draft dict(s)"},
        ],
        calls="AdaptationDAO, ml.adaptation",
        called_by="api/routers/cae.py",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "11. Similarity / relevancy / duplicates / credibility", 1)
    concept_block(
        doc,
        "11.1 Concept: TF-IDF + cosine similarity",
        meaning="Convert texts to weighted term vectors; score similarity by cosine of the angle between vectors.",
        why="Find related or duplicate stories without neural embeddings.",
        how_works="Fit/transform TF-IDF on a corpus; cosine_similarity yields scores in roughly 0..1 for ranking.",
        in_project="ml/common/similarity.rank and similar_pairs; knowledge base uses published content as corpus.",
        related="Journalist tools, editor pitch duplicates",
    )
    file_block(
        doc,
        "ml/common/similarity.py",
        purpose="Shared ranking and near-duplicate pair finding.",
        libraries=[("sklearn.feature_extraction.text.TfidfVectorizer", "Vectorize text"), ("sklearn.metrics.pairwise.cosine_similarity", "Score pairs")],
        methods=[
            {"name": "rank(query, documents, *, limit=10)", "resp": "Top similar docs for a query string.", "params": "query str; list of doc dicts; limit", "returns": "list ranked dicts"},
            {"name": "similar_pairs(documents, *, threshold=0.5, limit=20)", "resp": "Pairs above similarity threshold.", "params": "docs; threshold; limit", "returns": "list pair dicts"},
        ],
        calls="sklearn",
        called_by="knowledge.base, duplicate_check, evidence_search, editor pitch duplicates",
    )
    file_block(
        doc,
        "ml/knowledge/base.py",
        purpose="Build published-content corpus; score relevancy for journalist tools.",
        libraries=[("ml.common.rank", "Similarity"), ("database.connection", "Load published rows")],
        methods=[
            {"name": "load_published_documents(limit=2000)", "resp": "Fetch published non-seed content.", "params": "limit", "returns": "list docs"},
            {"name": "score_content_relevancy(title, body='', *, limit=8, min_score=0.08)", "resp": "Rank matches + relevancy label/scores.", "params": "title/body/limit/min_score", "returns": "dict result", "calls": "load_published_documents; rank"},
        ],
        calls="db_cursor, ml.common",
        called_by="JournalistModule.related_content; content_validate",
    )
    file_block(
        doc,
        "services/journalist/credibility.py (+ evidence_search, duplicate_check, content_validate)",
        purpose="Journalist AI assist helpers.",
        libraries=[("ml.common", "rank/similar_pairs"), ("ml.knowledge", "relevancy"), ("utils.validators", "validate_content_record")],
        methods=[
            {"name": "assess_credibility(text, evidence_docs=None, *, limit=5)", "resp": "Claim-level support summary.", "params": "text; evidence list; limit", "returns": "claims+summary dict"},
            {"name": "search_evidence(query, documents=None, *, limit=10)", "resp": "Rank evidence docs.", "params": "query + docs", "returns": "list"},
            {"name": "find_duplicates(documents=None, *, threshold=0.5, limit=20)", "resp": "Near-duplicate pairs.", "params": "docs/threshold/limit", "returns": "pairs"},
            {"name": "validate_article(record=None)", "resp": "Field errors + relevancy block.", "params": "mapping", "returns": "ok/errors/relevancy fields"},
        ],
        calls="ml.common, ml.knowledge, validators",
        called_by="JournalistModule",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "12. ML training orchestration", 1)
    concept_block(
        doc,
        "12.1 Concept: Offline training pipeline",
        meaning="Datasets are cleaned/pushed into staging tables, models are fitted, artifacts written to disk for later inference.",
        why="Keeps heavy training off the request path.",
        how_works="Push CSV → ml_train_* → train_urgency_from_db / train_cae_from_db → artifacts/models/…",
        in_project="ml/training/ingest_clean.py + console.py; admin console ML menu; python -m ml.training",
        related="joblib artifacts, pandas",
    )
    file_block(
        doc,
        "ml/training/console.py & ingest_clean.py",
        purpose="Push datasets and train urgency/CAE models.",
        libraries=[("pandas", "Load frames"), ("sklearn/xgboost", "Fit estimators"), ("joblib", "Save artifacts"), ("CleaningOrchestrator", "Reuse cleaners"), ("psycopg2 via db", "Read/write staging")],
        methods=[
            {"name": "push_urgency_file / push_adaptation_file / push_all_new", "resp": "Ingest dataset CSVs into ml_train_* with hash skip.", "params": "paths/force flags", "returns": "stats"},
            {"name": "train_urgency_from_db(fast=False) / train_cae_from_db() / train_all", "resp": "Fit and write artifacts.", "params": "fast skips heavy search", "returns": "metrics/summary"},
            {"name": "main() CLI", "resp": "Argparse entry for --push-only/--urgency/--cae/--all/--fast.", "params": "CLI argv", "returns": "exit code"},
        ],
        calls="DB, cleaners, ml.adaptation.training, sklearn/xgboost, joblib",
        called_by="Shell `python -m ml.training`; app.py admin ML menu",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "13. API routers pattern (all desks)", 1)
    concept_block(
        doc,
        "13.1 Concept: Thin router",
        meaning="HTTP layer parses input, checks auth capability, calls service/module, maps errors—no SQL in routers.",
        why="Keeps transport concerns separate from business rules.",
        how_works="APIRouter(prefix, tags) + Depends(get_session_token) + Pydantic body + try/except raise_http_error.",
        in_project="api/routers/auth.py, journalist.py, aia.py, cae.py, publisher.py, editor.py, manager.py, admin.py",
        related="deps, schemas, http_errors",
    )
    H.table(
        doc,
        ["Router file", "Prefix", "Typically calls"],
        [
            ["auth.py", "/auth", "authenticate, logout, change_password, UserService.reset_password"],
            ["journalist.py", "/journalist", "JournalistModule methods"],
            ["aia.py", "/aia", "AIAService + CAP_ANALYTICS"],
            ["cae.py", "/cae", "AdaptationService + ReviewService + CAP_ADAPT"],
            ["publisher.py", "/publisher", "PublisherService + CAP_PUBLISH"],
            ["editor.py", "/editor", "EditorService + pitch/content/assign caps"],
            ["manager.py", "/manager", "ManagerService + analytics/review caps"],
            ["admin.py", "/admin", "AdminModule + UserService + ContentService category"],
        ],
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "14. Console CLI & easy UI", 1)
    concept_block(
        doc,
        "14.1 Concept: Shared business logic, multiple UIs",
        meaning="CLI and HTML tester are alternative presentations over the same modules/services/auth.",
        why="Operators and learners can choose menu or browser without duplicating rules.",
        how_works="CLI uses resolve_session file JWT; easy.html stores JWT in localStorage and calls fetch with Bearer.",
        in_project="app.py + utils/console_ui.py; api/static/easy.html",
        related="JWT, RBAC menus",
    )
    file_block(
        doc,
        "app.py",
        purpose="Interactive menus and argparse ops for pipeline/auth/content/ML.",
        libraries=[("argparse", "CLI flags"), ("getpass", "Password prompt"), ("modules/services/database", "Business ops"), ("utils.console_ui", "UX")],
        methods=[
            {"name": "do_login / do_logout / interactive / main", "resp": "Auth and menu loop / flag dispatch.", "params": "CLI args or prompts", "returns": "process exit codes"},
            {"name": "_run_admin(fn, title=...)", "resp": "Run admin action and pretty-print result dict.", "params": "callable returning dict", "returns": "0/1"},
        ],
        calls="AdminModule, ContentModule, UserService, auth_service, init_schema",
        called_by="python app.py …",
    )
    file_block(
        doc,
        "api/static/easy.html",
        purpose="Browser form console for nearly all endpoints.",
        libraries=[("Browser fetch API", "HTTP JSON calls"), ("localStorage", "Persist JWT/user/role")],
        methods=[
            {"name": "api(method, path, body)", "resp": "Build headers (Bearer) and fetch JSON.", "params": "HTTP method/path/body object", "returns": "parsed result / throws on error"},
            {"name": "GROUPS config", "resp": "Declarative map of UI sections → endpoints → fields.", "params": "n/a (data)", "returns": "drives form rendering"},
        ],
        calls="Backend REST API only",
        called_by="Browser at GET /easy",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "15. Testing & logging concepts", 1)
    concept_block(
        doc,
        "15.1 Concept: API testing with TestClient",
        meaning="In-process HTTP client exercises the real app without a network port.",
        why="Fast regression checks for auth and desks.",
        how_works="TestClient(app) sends requests; assertions on status/JSON; fixtures login with DEMO_PASSWORDS and logout.",
        in_project="tests/test_api_*.py + conftest db_ready",
        related="pytest",
    )
    file_block(
        doc,
        "tests/conftest.py + test_api_*.py + pipeline tests",
        purpose="Path setup, DB skip fixture, endpoint and ETL tests.",
        libraries=[("pytest", "Fixtures/asserts"), ("fastapi.testclient.TestClient", "HTTP"), ("DEMO_PASSWORDS", "Login")],
        methods=[
            {"name": "db_ready fixture", "resp": "Skip if DB/schema unavailable.", "params": "pytest fixture", "returns": "marks tests"},
            {"name": "client fixtures", "resp": "Yield TestClient; logout around tests.", "params": "depends db_ready", "returns": "client"},
        ],
        calls="api.main.app, auth logout",
        called_by="pytest runner",
    )
    file_block(
        doc,
        "utils/logger.py / progress.py / errors.py",
        purpose="Cross-cutting diagnostics and typed errors.",
        libraries=[("logging", "Standard logging"), ("Path helpers", "logs directory")],
        methods=[
            {"name": "get_logger(name)", "resp": "Configured logger.", "params": "name str", "returns": "Logger"},
            {"name": "progress(message)", "resp": "Human + log pipeline step.", "params": "message", "returns": "None"},
            {"name": "AppError hierarchy", "resp": "Validation/NotFound/Auth/PermissionDenied with .message", "params": "message str", "returns": "exception instances"},
        ],
        calls="stdlib logging",
        called_by="Entire application",
    )
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════════
    H.h(doc, "16. Library catalog (project-wide)", 1)
    H.table(
        doc,
        ["Library", "Used for", "Main places"],
        [
            ["FastAPI", "HTTP API, Depends, OpenAPI", "api/*"],
            ["Uvicorn", "Run ASGI app", "README run command"],
            ["Pydantic", "Request/response validation", "api/schemas/*"],
            ["PyJWT", "Sign/verify access tokens", "modules/authentication/security.py"],
            ["psycopg2", "Postgres driver", "database/connection.py, dao/*"],
            ["pandas", "CSV chunk ingest / training frames", "ingestion_service, ml/training"],
            ["scikit-learn", "TF-IDF, cosine, LR pipelines", "ml/common, ml/adaptation, training"],
            ["XGBoost", "Urgency classifier", "ml/training urgency, editor model"],
            ["joblib", "Serialize/load ML artifacts", "artifacts loaders"],
            ["numpy/scipy", "Numeric/sparse features", "ml/editor, ml/adaptation"],
            ["spaCy (optional)", "Entity extraction helper", "ml/common/entities.py"],
            ["pytest / httpx", "Tests / TestClient transport", "tests/*"],
            ["stdlib hashlib/hmac/secrets", "PBKDF2, compare, jti/randomness", "security.py"],
            ["stdlib argparse/getpass/json", "CLI UX and session file", "app.py, auth_service"],
        ],
    )

    H.h(doc, "17. How to study with this guide", 1)
    H.numbered(doc, "Pick one concept chapter (example: JWT).")
    H.numbered(doc, "Read concept explanation until clear.")
    H.numbered(doc, "Read each file block: methods, parameters, calls.")
    H.numbered(doc, "Trace the numbered flow.")
    H.numbered(doc, "Open only those files in the IDE and locate the named methods.")
    H.numbered(doc, "Move to the next desk/ETL/ML chapter using the same pattern.")

    H.h(doc, "Closing", 1)
    H.p(
        doc,
        "This document explains NewsMindAI V2 concept-by-concept and file-by-file: what each idea means, "
        "which file owns it, which methods exist, what parameters they take, what they call, who calls "
        "them, and which libraries support them—without dumping full source listings.",
    )

    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    doc.save(OUT_DOCX)
    return OUT_DOCX


def main() -> int:
    print("Building detailed concept+file guide...")
    path = build()
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
