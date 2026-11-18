"""FastAPI app — Swagger UI at /docs."""

from __future__ import annotations

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from api.routers import (
    admin_router,
    aia_router,
    auth_router,
    cae_router,
    editor_router,
    journalist_router,
    manager_router,
    publisher_router,
)
from config.env_loader import load_dotenv
from utils.logger import get_logger

log = get_logger("api")
STATIC_DIR = Path(__file__).resolve().parent / "static"

OPENAPI_TAGS = [
    {
        "name": "1. Login",
        "description": "Login, logout, change password, admin reset. Authorize with Bearer token.",
    },
    {
        "name": "2. Journalist tools",
        "description": "AI tools + desk content (news/articles/evidence/raw ingest).",
    },
    {
        "name": "3. Audience Insight Analyst",
        "description": "Heuristic engagement/interest, category/trends, performance loop, story pitches.",
    },
    {
        "name": "4. Content Adaptation (CAE)",
        "description": "Adapt articles for social, print, web, and newsletter; review drafts.",
    },
    {
        "name": "5. Publisher",
        "description": "Publication queue, templates, preview, publish, and schedule.",
    },
    {
        "name": "6. Editor",
        "description": "Pitch review, content review, and assignment.",
    },
    {
        "name": "7. Newsroom Manager",
        "description": "Desk overview plus pitch/content review and assignment.",
    },
    {
        "name": "8. Admin",
        "description": "Data pipeline (ingest/clean/persist) and user/category admin.",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_dotenv()
    log.info("NewsMind API started. Swagger: /docs")
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="NewsMind API",
        summary="Login once, Authorize, then use role tools in Swagger.",
        description=(
            "### Quick start\n"
            "1. Open **1. Login** → `POST /auth/login` → Try it out\n"
            "2. Copy `session_token` from the response\n"
            "3. Click **Authorize** → paste token → Authorize\n"
            "4. Use role endpoints (Journalist, AIA, CAE, Publisher, Editor, Manager)\n\n"
            "### Password rules (change/reset)\n"
            "Min 10 characters, with uppercase, lowercase, digit, and special character.\n\n"
            "Models: `editor_queue_urgency.joblib` (editor review urgency) and "
            "`cae/` (unified content adaptation). Engagement/interest/trend are formulas; "
            "category is manual. See `ml/README.md` and `docs/NAMING.md`.\n\n"
            "Simple tester UI (easier than Swagger): **/easy**"
        ),
        version="0.3.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
        openapi_tags=OPENAPI_TAGS,
        swagger_ui_parameters={
            "docExpansion": "list",
            "defaultModelsExpandDepth": -1,
            "defaultModelExpandDepth": 1,
            "filter": True,
            "tryItOutEnabled": True,
            "persistAuthorization": True,
        },
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/easy", include_in_schema=False)
    def easy_tester() -> FileResponse:
        return FileResponse(STATIC_DIR / "easy.html")

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", ()) if part != "body")
            errors.append({"field": loc or "body", "message": err.get("msg", "Invalid value")})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation failed", "errors": errors},
        )

    application.include_router(auth_router)
    application.include_router(journalist_router)
    application.include_router(aia_router)
    application.include_router(cae_router)
    application.include_router(publisher_router)
    application.include_router(editor_router)
    application.include_router(manager_router)
    application.include_router(admin_router)
    return application


app = create_app()
