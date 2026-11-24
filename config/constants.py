"""Application constants — roles/RBAC match your main config/constants.py."""

from __future__ import annotations

import os

from config.env_loader import load_dotenv

load_dotenv()

ALLOWED_CONTENT_STATUSES = ("draft", "submitted", "approved", "rejected", "published", "rework")
ALLOWED_PITCH_STATUSES = ("submitted", "approved", "rejected", "hold", "closed")
ALLOWED_ACCOUNT_STATUSES = ("active", "inactive", "locked")

MIN_TITLE_LENGTH = 5
MIN_BODY_LENGTH = 40
MAX_TITLE_LENGTH = 512

CONTENT_KINDS = ("article", "news")

# Topics the category model is trained to predict (+ a few manual desk labels)
DEFAULT_CATEGORIES = (
    "Politics",
    "Sports",
    "Business",
    "Entertainment",
    "World",
    "City",
    "Weather",
)

# Roles (your ERD desks + admin)
ROLE_ADMIN = "administrator"
ROLE_AUDIENCE_ANALYST = "audience_insight_analyst"
ROLE_JOURNALIST = "journalist"
ROLE_EDITOR = "editor"
ROLE_ADAPTATION_EDITOR = "content_adaptation_editor"
ROLE_PUBLISHER = "publisher"
ROLE_NEWSROOM_MANAGER = "newsroom_manager"

ALL_ROLES = (
    ROLE_ADMIN,
    ROLE_AUDIENCE_ANALYST,
    ROLE_JOURNALIST,
    ROLE_EDITOR,
    ROLE_ADAPTATION_EDITOR,
    ROLE_PUBLISHER,
    ROLE_NEWSROOM_MANAGER,
)

ROLE_DISPLAY_NAMES = {
    ROLE_ADMIN: "Administrator",
    ROLE_AUDIENCE_ANALYST: "Audience Insight Analyst",
    ROLE_JOURNALIST: "Journalist",
    ROLE_EDITOR: "Editor",
    ROLE_ADAPTATION_EDITOR: "Content Adaptation Editor",
    ROLE_PUBLISHER: "Publisher",
    ROLE_NEWSROOM_MANAGER: "Newsroom Manager",
}

# CAE target platforms
PLATFORM_SOCIAL = "SOCIAL_MEDIA"
PLATFORM_PRINT = "PRINT_NEWSPAPER"
PLATFORM_WEB = "WEBSITE"
PLATFORM_EMAIL = "EMAIL_NEWSLETTER"
ADAPTATION_PLATFORMS = (PLATFORM_SOCIAL, PLATFORM_PRINT, PLATFORM_WEB, PLATFORM_EMAIL)
PLATFORM_SENTENCE_LIMITS = {
    PLATFORM_SOCIAL: 2,
    PLATFORM_EMAIL: 5,
    PLATFORM_PRINT: 8,
    PLATFORM_WEB: 10,
}

PUBLICATION_TEMPLATES = (
    {"code": "web_standard", "name": "Website standard", "channel": "website"},
    {"code": "print_column", "name": "Print column", "channel": "print"},
    {"code": "social_short", "name": "Social short", "channel": "social"},
    {"code": "newsletter", "name": "Email newsletter", "channel": "email"},
)

# Capability keys for RBAC (pipeline / desks)
CAP_INGEST = "ingest"
CAP_CLEAN = "clean"
CAP_PERSIST = "persist"
CAP_PIPELINE = "pipeline"
CAP_PITCH_REVIEW = "pitch_review"
CAP_CONTENT_REVIEW = "content_review"
CAP_ASSIGN = "assign"
CAP_ADAPT = "adapt"
CAP_PUBLISH = "publish"
CAP_ANALYTICS = "analytics"
CAP_ADMIN = "admin"
CAP_MANAGE_USERS = "manage_users"
CAP_JOURNALIST_TOOLS = "journalist_tools"

ROLE_CAPABILITIES = {
    ROLE_ADMIN: (
        CAP_INGEST,
        CAP_CLEAN,
        CAP_PERSIST,
        CAP_PIPELINE,
        CAP_PITCH_REVIEW,
        CAP_CONTENT_REVIEW,
        CAP_ASSIGN,
        CAP_ADAPT,
        CAP_PUBLISH,
        CAP_ANALYTICS,
        CAP_ADMIN,
        CAP_MANAGE_USERS,
        CAP_JOURNALIST_TOOLS,
    ),
    # Analyst uses /aia only (not editor pitch-review desk)
    ROLE_AUDIENCE_ANALYST: (CAP_INGEST, CAP_CLEAN, CAP_ANALYTICS),
    ROLE_JOURNALIST: (CAP_JOURNALIST_TOOLS,),
    ROLE_EDITOR: (CAP_PITCH_REVIEW, CAP_CONTENT_REVIEW, CAP_ASSIGN, CAP_ANALYTICS),
    ROLE_ADAPTATION_EDITOR: (CAP_ADAPT,),
    ROLE_PUBLISHER: (CAP_PUBLISH,),
    ROLE_NEWSROOM_MANAGER: (
        CAP_PITCH_REVIEW,
        CAP_CONTENT_REVIEW,
        CAP_ASSIGN,
        CAP_ADAPT,
        CAP_PUBLISH,
        CAP_ANALYTICS,
        CAP_MANAGE_USERS,
    ),
}

# Security (same policy as main app)
PASSWORD_HASH_ITERATIONS = 120_000
PASSWORD_SALT_BYTES = 16
SESSION_TTL_HOURS = 12
LOGIN_LOCKOUT_MINUTES = 15
MAX_LOGIN_FAILURES = 5

# JWT access tokens (HS256). NEWSROOM_JWT_SECRET must be set in .env (no code fallback).
JWT_ALGORITHM = "HS256"


def get_jwt_secret() -> str:
    load_dotenv()
    secret = os.environ.get("NEWSROOM_JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "NEWSROOM_JWT_SECRET is not set. Add it to your .env file (see ENV.example)."
        )
    return secret

# Demo passwords (local only)
DEMO_PASSWORDS = {
    "admin": "Admin@NewsMind2026!",
    "analyst": "Analyst@NewsMind2026!",
    "journalist": "Journalist@NewsMind2026!",
    "journalist2": "Journalist@NewsMind2026!",
    "journalist3": "Journalist@NewsMind2026!",
    "editor": "Editor@NewsMind2026!",
    "adapter": "Adapter@NewsMind2026!",
    "publisher": "Publisher@NewsMind2026!",
    "manager": "Manager@NewsMind2026!",
}
