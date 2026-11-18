"""
NewsMind console application.

Feature modules: authentication, admin, content
Services: pipeline at services/ root; content/ + user/ grouped
Cleaning: cleaners/ (+ stages/) | Repositories: content + user
Menus are role-based after login.
"""

from __future__ import annotations

import argparse
import json
import sys
from getpass import getpass
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.constants import (
    ALLOWED_CONTENT_STATUSES,
    ALLOWED_PITCH_STATUSES,
    CAP_ADMIN,
    CAP_CLEAN,
    CAP_INGEST,
    CAP_PERSIST,
    CAP_PIPELINE,
    CAP_PITCH_REVIEW,
    ROLE_ADMIN,
    ROLE_ADAPTATION_EDITOR,
    ROLE_AUDIENCE_ANALYST,
    ROLE_EDITOR,
    ROLE_JOURNALIST,
    ROLE_NEWSROOM_MANAGER,
    ROLE_PUBLISHER,
)
from config.env_loader import load_dotenv
from database.connection import check_connection, init_schema
from modules.admin import AdminModule
from modules.authentication import (
    AuthenticationError,
    authenticate,
    change_password,
    logout,
    resolve_session,
)
from modules.content import ContentModule
from services.permission_service import has_capability
from services.user import UserService
from utils.console_ui import (
    UserCancelled,
    blank,
    error,
    header,
    info,
    is_cancel,
    kv,
    prompt_choice,
    prompt_nonempty,
    prompt_optional,
    show_dict_rows,
    show_stats,
    show_user,
    success,
)
from utils.errors import AppError, AuthError, PermissionDeniedError, ValidationError
from utils.logger import get_logger
from utils.validators import require_pitch_status

load_dotenv()

log = get_logger("app")
admin = AdminModule()
content = ContentModule()
users = UserService()

Action = Callable[[], int]


def _current_user() -> Optional[dict[str, Any]]:
    try:
        return resolve_session()
    except AuthenticationError:
        return None


def _handle(exc: Exception) -> int:
    if isinstance(exc, UserCancelled):
        raise exc
    if isinstance(exc, AppError):
        error(exc.message)
        return 1
    if isinstance(exc, AuthenticationError):
        error(str(exc))
        return 1
    # Database / driver errors — show the useful message, not a raw stack only
    try:
        from psycopg2 import Error as PgError
    except ImportError:  # pragma: no cover
        PgError = ()  # type: ignore[misc, assignment]
    if PgError and isinstance(exc, PgError):
        log.exception("Database error")
        error(f"Database error: {exc}")
        info("Tip: run menu DB status / python app.py --init-db if schema is outdated.")
        return 1
    if isinstance(exc, (FileNotFoundError, RuntimeError, ValueError)):
        error(str(exc))
        return 1
    log.exception("Unhandled error")
    error(f"Unexpected failure: {exc}")
    return 1


def _run_admin(fn, *, title: str) -> int:
    try:
        result = fn()
    except UserCancelled:
        raise
    except (AuthError, PermissionDeniedError, AppError) as exc:
        return _handle(exc)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)

    header(title)
    kv("Actor", result.get("actor"))
    kv("Role", result.get("role"))
    if result.get("message"):
        info(str(result["message"]))
    if "all_files" in result:
        kv("CSV Files", len(result.get("all_files") or []))
        for name in result.get("all_files") or []:
            mark = " [new/changed]" if name in (result.get("new_or_changed") or []) else ""
            print(f"    - {name}{mark}")
        kv("New Or Changed", len(result.get("new_or_changed") or []))
    if "content_rows" in result:
        kv("Content Rows", result["content_rows"])
        kv("Pitch Rows", result.get("pitch_rows"))
        files = result.get("source_files") or []
        kv("Source Files", len(files))
        for name in files[:20]:
            print(f"    - {name}")
        if len(files) > 20:
            print(f"    ... and {len(files) - 20} more")
        collections = result.get("collections") or {}
        if collections:
            kv("Categories", ", ".join(collections.get("categories") or []) or "none")
            kv("Unique Titles", collections.get("unique_titles"))
        kv("Raw Rows Stored", len(result.get("raw_ingest_ids") or []))
    if "ingest" in result:
        ingest = result["ingest"]
        kv("Ingested Content", ingest.get("content_rows"))
        kv("Ingested Pitches", ingest.get("pitch_rows"))
        kv("Raw Stored", ingest.get("raw_stored"))
        files = ingest.get("source_files") or []
        kv("Source Files", len(files))
        for name in files[:20]:
            print(f"    - {name}")
    if "content_stats" in result:
        stats = result["content_stats"]
        kv("Clean Kept", stats.get("kept"))
        kv("Clean Rejected", stats.get("rejected"))
        kv("Quality Report File", result.get("content_report") or result.get("quality_report"))
        kv("Cleaning Report ID", result.get("cleaning_report_id"))
        kv("Cleaned CSV", result.get("cleaned_csv"))
    if "persisted_content" in result:
        kv("Persisted Content", result.get("persisted_content"))
        kv("Persisted Pitches", result.get("persisted_pitches"))
        kv("Rejected Raw Stored", result.get("rejected_raw_stored"))
    success(f"{title} completed.")
    blank()
    return 0


# ── Auth ──────────────────────────────────────────────────────────────────────

def do_login(username: str = "", password: str = "") -> int:
    try:
        username = username or prompt_nonempty("Username")
        password = password or getpass("Password: ")
        if not password:
            raise ValidationError("Password cannot be empty.")
        payload = authenticate(username, password)
    except (AuthenticationError, ValidationError, AppError) as exc:
        return _handle(exc)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    success("Login successful.")
    show_user(payload)
    return 0


def do_logout() -> int:
    logout()
    success("Logged out.")
    blank()
    return 0


def do_change_password() -> int:
    header("Change Password")
    try:
        user = resolve_session()
        current = getpass("Current password: ")
        new_password = getpass("New password: ")
        confirm = getpass("Confirm new password: ")
        if new_password != confirm:
            raise ValidationError("New password and confirmation do not match.")
        change_password(int(user["user_id"]), current, new_password)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    success("Password changed. Use the new password next login.")
    blank()
    return 0


def do_admin_reset_password() -> int:
    header("Reset User Password (Admin)")
    try:
        username = prompt_nonempty("Username to reset")
        new_password = getpass("New password: ")
        confirm = getpass("Confirm new password: ")
        if new_password != confirm:
            raise ValidationError("New password and confirmation do not match.")
        result = users.reset_password(username, new_password)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    success("Password reset for user.")
    kv("Username", result["username"])
    kv("User ID", result["user_id"])
    blank()
    return 0


# ── Admin / pipeline ──────────────────────────────────────────────────────────

def do_list_csv_files() -> int:
    return _run_admin(admin.list_csv_files, title="CSV Files In data/raw")


def do_ingest() -> int:
    return _run_admin(lambda: admin.ingest(only_new=False), title="Ingest All CSV Files")


def do_ingest_new() -> int:
    return _run_admin(lambda: admin.ingest(only_new=True), title="Ingest New/Changed CSV Files")


def do_ingest_one() -> int:
    header("Ingest One CSV File")
    try:
        listing = admin.list_csv_files()
        files = listing.get("all_files") or []
        if not files:
            raise ValidationError("No CSV files found under data/raw.")
        info(f"{len(files)} CSV file(s) available.")
        for idx, name in enumerate(files, start=1):
            mark = " [new/changed]" if name in (listing.get("new_or_changed") or []) else ""
            print(f"  {idx}) {name}{mark}")
        choice = prompt_nonempty("File number or relative path")
        if choice.isdigit():
            n = int(choice)
            if n < 1 or n > len(files):
                raise ValidationError("File number out of range.")
            source = files[n - 1]
        else:
            source = choice
        return _run_admin(lambda: admin.ingest_file(source), title=f"Ingest File — {source}")
    except (AuthError, PermissionDeniedError, AppError, UserCancelled) as exc:
        if isinstance(exc, UserCancelled):
            raise
        return _handle(exc)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)


def do_clean() -> int:
    return _run_admin(admin.clean, title="Clean Data")


def do_ingest_and_clean() -> int:
    return _run_admin(lambda: admin.ingest_and_clean(only_new=False), title="Ingest + Clean (All)")


def do_ingest_and_clean_new() -> int:
    return _run_admin(lambda: admin.ingest_and_clean(only_new=True), title="Ingest + Clean (New Only)")


def do_persist() -> int:
    return _run_admin(admin.persist, title="Persist Cleaned Data")


def do_pipeline() -> int:
    return _run_admin(lambda: admin.run_pipeline(only_new=False), title="Full Pipeline (All Files)")


def do_pipeline_new() -> int:
    return _run_admin(lambda: admin.run_pipeline(only_new=True), title="Full Pipeline (New Files Only)")


def do_pipeline_one() -> int:
    header("Pipeline One CSV File")
    try:
        listing = admin.list_csv_files()
        files = listing.get("all_files") or []
        if not files:
            raise ValidationError("No CSV files found under data/raw.")
        for idx, name in enumerate(files, start=1):
            mark = " [new/changed]" if name in (listing.get("new_or_changed") or []) else ""
            print(f"  {idx}) {name}{mark}")
        choice = prompt_nonempty("File number or relative path")
        if choice.isdigit():
            n = int(choice)
            if n < 1 or n > len(files):
                raise ValidationError("File number out of range.")
            source = files[n - 1]
        else:
            source = choice
        return _run_admin(lambda: admin.pipeline_file(source), title=f"Pipeline File — {source}")
    except (AuthError, PermissionDeniedError, AppError, UserCancelled) as exc:
        if isinstance(exc, UserCancelled):
            raise
        return _handle(exc)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)


def do_list_reports() -> int:
    try:
        payload = admin.list_reports(limit=20)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    show_dict_rows(
        "Cleaning Reports (DB)",
        payload.get("reports") or [],
        [
            ("Report ID", "cleaning_report_id"),
            ("Type", "report_type"),
            ("Input", "input_count"),
            ("Kept", "kept_count"),
            ("Rejected", "rejected_count"),
            ("Sources", "source_files"),
            ("Created", "created_at"),
        ],
    )
    return 0


def do_view_report() -> int:
    header("View Cleaning Report")
    try:
        report_id = int(prompt_nonempty("Cleaning report ID"))
        payload = admin.view_report(report_id)
        row = payload["report"]
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    kv("Report ID", row.get("cleaning_report_id"))
    kv("Type", row.get("report_type"))
    kv("Source Files", row.get("source_files"))
    kv("Input", row.get("input_count"))
    kv("Kept", row.get("kept_count"))
    kv("Rejected", row.get("rejected_count"))
    kv("Created", row.get("created_at"))
    report_json = row.get("report_json")
    if report_json is not None:
        if isinstance(report_json, str):
            try:
                report_json = json.loads(report_json)
            except json.JSONDecodeError:
                pass
        print("  Report detail:")
        print(json.dumps(report_json, indent=2, default=str)[:4000])
    blank()
    return 0


def do_status() -> int:
    ok = check_connection()
    header("Database Status")
    kv("Connected", "Yes" if ok else "No")
    blank()
    return 0 if ok else 1


def _require_admin_ml() -> dict[str, Any]:
    user = _current_user()
    if user is None:
        raise AuthError("Login required.")
    role = user["role_code"]
    caps = set(user.get("capabilities") or [])
    if role != ROLE_ADMIN and CAP_ADMIN not in caps:
        raise PermissionDeniedError("Admin capability required for ML training.")
    return user



def do_push_urgency_datasets() -> int:
    try:
        _require_admin_ml()
        from ml.training import push_urgency
        from ml.training.ingest_clean import list_dataset_csvs

        files = list_dataset_csvs("urgency")
        header("Push Urgency Datasets (ingest + clean)")
        if not files:
            info("No CSV files found under ml/editor/dataset/")
            blank()
            return 1
        info(f"Auto-detected {len(files)} file(s): " + ", ".join(files))
        n = push_urgency()  # all detected; skips unchanged hashes
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    kv("Rows", n)
    success("Urgency push finished.")
    blank()
    return 0


def do_push_adaptation_datasets() -> int:
    try:
        _require_admin_ml()
        from ml.training import push_adaptation
        from ml.training.ingest_clean import list_dataset_csvs

        files = list_dataset_csvs("adaptation")
        header("Push CAE Datasets (ingest + clean)")
        if not files:
            info("No CSV files found under ml/adaptation/dataset/")
            blank()
            return 1
        info(f"Auto-detected {len(files)} file(s): " + ", ".join(files))
        n = push_adaptation()  # all detected; skips unchanged hashes
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    kv("Rows", n)
    success("CAE push finished.")
    blank()
    return 0


def do_train_urgency() -> int:
    try:
        _require_admin_ml()
        from ml.training import train_urgency_from_db

        # Fast mode for console: full CV search can look "stuck" for many minutes
        info("Training urgency (fast mode). Watch step logs 1/6 … 6/6.")
        metrics = train_urgency_from_db(fast=True)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    header("Train Urgency Model")
    kv("Accuracy", metrics.get("accuracy"))
    kv("Macro F1", metrics.get("macro_f1"))
    kv("Train rows", metrics.get("n_train"))
    kv("Test rows", metrics.get("n_test"))
    success("Urgency training completed.")
    blank()
    return 0


def do_train_cae() -> int:
    try:
        _require_admin_ml()
        from ml.training import train_cae_from_db

        results = train_cae_from_db()
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    header("Train Unified CAE Model")
    block = results.get("content_adaptation") or {}
    test = (block.get("metrics") or {}).get("test") or {}
    kv("Overall F1", test.get("f1"))
    kv("Overall accuracy", test.get("accuracy"))
    for platform, stats in (block.get("per_platform") or {}).items():
        f1 = stats.get("f1")
        acc = stats.get("accuracy")
        kv(
            platform,
            f"F1={f1:.4f} acc={acc:.4f}" if f1 is not None and acc is not None else "see console output",
        )
    success("Unified CAE training completed.")
    blank()
    return 0


def do_train_all_models() -> int:
    try:
        _require_admin_ml()
        from ml.training import train_all

        info("Training all models (urgency uses fast mode). Step logs will print below.")
        summary = train_all(fast=True)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    header("Train All Models (urgency + CAE + KB)")
    urg = summary.get("editor_queue_urgency") or {}
    kv("Urgency accuracy", urg.get("accuracy"))
    kv("Urgency macro F1", urg.get("macro_f1"))
    cae = summary.get("cae_adaptation") or {}
    for platform, stats in cae.items():
        f1 = stats.get("test_f1")
        kv(platform, f"test F1={f1:.4f}" if f1 is not None else "see console output")
    success("All model training completed.")
    blank()
    return 0


def do_init_db() -> int:
    try:
        init_schema()
        ok = check_connection()
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    header("Initialize Database")
    kv("Schema", "Applied")
    kv("Connected", "Yes" if ok else "No")
    success("Database ready.")
    blank()
    return 0 if ok else 1


# ── Content / users ───────────────────────────────────────────────────────────

def do_add_user() -> int:
    header("Add User")
    try:
        result = users.add_user(
            username=prompt_nonempty("Username"),
            password=getpass("Password: "),
            first_name=prompt_nonempty("First name"),
            last_name=prompt_nonempty("Last name"),
            email=prompt_nonempty("Email"),
            role_code=prompt_optional("Role code", "journalist"),
        )
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    success("User created.")
    kv("User ID", result["user_id"])
    kv("Username", result["username"])
    kv("Role", result["role_code"])
    blank()
    return 0


def do_add_category() -> int:
    header("Add Category")
    try:
        cid = content.add_category(
            prompt_nonempty("Category name"),
            prompt_optional("Description"),
        )
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    success("Category created.")
    kv("Category ID", cid)
    blank()
    return 0


def do_add_pitch() -> int:
    header("Add Story Pitch")
    try:
        status = prompt_choice("Status", ALLOWED_PITCH_STATUSES) or "submitted"
        status = require_pitch_status(status)
        pid = content.add_pitch(
            prompt_nonempty("Title"),
            prompt_nonempty("Summary"),
            status=status,
        )
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    success("Story pitch created.")
    kv("Story Pitch ID", pid)
    blank()
    return 0


def do_add_news() -> int:
    header("Add News")
    try:
        status = prompt_choice("Status", ALLOWED_CONTENT_STATUSES) or "draft"
        evidence: list[dict[str, Any]] = []
        info("At least one evidence item is required.")
        while True:
            evidence.append(
                {
                    "title": prompt_nonempty("Evidence title"),
                    "evidence_type": prompt_optional("Evidence type", "document") or "document",
                    "source_url": prompt_optional("Evidence source URL"),
                    "text": prompt_optional("Evidence text (optional)"),
                }
            )
            more = prompt_optional("Add another evidence? (y/N)", "n").lower()
            if more != "y":
                break
        result = content.add_news(
            title=prompt_nonempty("Title"),
            body=prompt_nonempty("Body"),
            summary=prompt_optional("Summary"),
            event_location=prompt_optional("Event location"),
            severity=prompt_optional("Severity", "low"),
            breaking=prompt_optional("Breaking news? (y/N)", "n").lower() == "y",
            status=status,
            evidence=evidence,
        )
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    success("News created.")
    kv("Content ID", result["content_id"])
    kv("News ID", result["news_id"])
    kv("Evidence IDs", ", ".join(str(i) for i in result.get("evidence_ids") or []))
    blank()
    return 0


def do_add_article() -> int:
    header("Add Article")
    try:
        status = prompt_choice("Status", ALLOWED_CONTENT_STATUSES) or "draft"
        evidence: list[dict[str, Any]] = []
        info("At least one evidence item is required.")
        while True:
            evidence.append(
                {
                    "title": prompt_nonempty("Evidence title"),
                    "evidence_type": prompt_optional("Evidence type", "document") or "document",
                    "source_url": prompt_optional("Evidence source URL"),
                    "text": prompt_optional("Evidence text (optional)"),
                }
            )
            more = prompt_optional("Add another evidence? (y/N)", "n").lower()
            if more not in {"y", "yes"}:
                break
        result = content.add_article(
            title=prompt_nonempty("Title"),
            body=prompt_nonempty("Body"),
            summary=prompt_optional("Summary"),
            status=status,
            evidence=evidence,
        )
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    success("Article created.")
    kv("Content ID", result["content_id"])
    kv("Article ID", result["article_id"])
    kv("Evidence IDs", result.get("evidence_ids"))
    blank()
    return 0


def do_list_content() -> int:
    try:
        rows = content.list_content(limit=10)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    show_dict_rows(
        "Recent Content",
        rows,
        [
            ("Content ID", "content_id"),
            ("Title", "title"),
            ("Kind", "content_kind"),
            ("Status", "status"),
            ("Source", "source_type"),
        ],
    )
    return 0


def do_list_news() -> int:
    try:
        rows = content.list_news(limit=10)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    show_dict_rows(
        "Recent News",
        rows,
        [
            ("News ID", "news_id"),
            ("Content ID", "content_id"),
            ("Event Title", "event_title"),
            ("Severity", "severity"),
            ("Breaking", "breaking_news_flag"),
        ],
    )
    return 0


def do_list_raw() -> int:
    try:
        rows = content.list_raw(limit=15)
        counts = content.raw_counts()
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    show_stats("Raw Ingest Counts", counts or {"none": 0})
    show_dict_rows(
        "Recent Raw Ingest",
        rows,
        [
            ("Raw ID", "raw_ingest_id"),
            ("Source File", "source_file"),
            ("Title", "title"),
            ("Category", "category"),
            ("Cleaning Status", "cleaning_status"),
            ("Reject Reason", "reject_reason"),
            ("Content ID", "content_id"),
        ],
    )
    return 0


def do_view_content() -> int:
    header("View Content By ID")
    try:
        row = content.get_content(prompt_nonempty("Content ID"))
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    kv("Content ID", row["content_id"])
    kv("Title", row.get("title"))
    kv("Kind", row.get("content_kind"))
    kv("Status", row.get("status"))
    kv("Source", row.get("source_type"))
    kv("Summary", row.get("summary"))
    kv("Raw Body", (row.get("raw_body") or "")[:180])
    kv("Clean Body", (row.get("content_body") or "")[:180])
    blank()
    return 0


def do_update_content_status() -> int:
    header("Update Content Status")
    try:
        content_id = content.get_content(prompt_nonempty("Content ID"))["content_id"]
        status = prompt_choice("New status", ALLOWED_CONTENT_STATUSES)
        if status is None:
            raise ValidationError("Status is required.")
        result = content.update_status(content_id, status)
    except Exception as exc:  # noqa: BLE001
        return _handle(exc)
    success("Content status updated.")
    kv("Content ID", result["content_id"])
    kv("Title", result["title"])
    kv("Status", result["status"])
    blank()
    return 0


# ── Role-based menu ───────────────────────────────────────────────────────────

def _build_menu(user: Optional[dict[str, Any]]) -> tuple[str, dict[str, Action]]:
    lines = [
        "",
        "=" * 56,
        "  NewsMind Console",
        "=" * 56,
    ]
    actions: dict[str, Action] = {}
    n = 1

    def add(label: str, fn: Action) -> None:
        nonlocal n
        key = str(n)
        lines.append(f"  {key}) {label}")
        actions[key] = fn
        n += 1

    lines.append("")
    lines.append("  AUTH")
    if user is None:
        add("Login", do_login)
        lines.append("  (login to unlock pipeline + role desk menus)")
        lines.append("  (password reset for users is admin-only after login)")
    else:
        add("Logout", do_logout)
        add("Change password", do_change_password)
        role = user["role_code"]
        caps = set(user.get("capabilities") or [])
        lines.append("")
        lines.append(f"  Logged in as - {user['username']}")
        lines.append(f"  Role - {user.get('role_name') or role}")

        pipeline_opts = [
            ("List CSV files (new/changed marked)", do_list_csv_files, CAP_INGEST),
            ("Ingest one CSV file", do_ingest_one, CAP_INGEST),
            ("Ingest new/changed CSV files only", do_ingest_new, CAP_INGEST),
            ("Ingest all CSV files", do_ingest, CAP_INGEST),
            ("Clean data", do_clean, CAP_CLEAN),
            ("Ingest + Clean (new only)", do_ingest_and_clean_new, CAP_CLEAN),
            ("Ingest + Clean (all)", do_ingest_and_clean, CAP_CLEAN),
            ("Persist cleaned data", do_persist, CAP_PERSIST),
            ("Pipeline one CSV file", do_pipeline_one, CAP_PIPELINE),
            ("Full pipeline (new files only)", do_pipeline_new, CAP_PIPELINE),
            ("Full pipeline (all files)", do_pipeline, CAP_PIPELINE),
            ("List cleaning reports (DB)", do_list_reports, CAP_CLEAN),
            ("View cleaning report by ID", do_view_report, CAP_CLEAN),
        ]
        visible = [(label, fn) for label, fn, cap in pipeline_opts if has_capability(role, cap)]
        if visible:
            lines.append("")
            lines.append("  DATA PIPELINE")
            for label, fn in visible:
                add(label, fn)

        lines.append("")
        lines.append(f"  {str(role).upper().replace('_', ' ')} DESK")

        if role == ROLE_ADMIN or CAP_ADMIN in caps:
            add("Add user", do_add_user)
            add("Reset user password", do_admin_reset_password)
            add("Add category", do_add_category)
            add("Add story pitch", do_add_pitch)
            add("Add news", do_add_news)
            add("Add article", do_add_article)
            add("View content by ID", do_view_content)
            add("Update content status", do_update_content_status)
            add("List content", do_list_content)
            add("List news", do_list_news)
            add("List raw ingest", do_list_raw)
            lines.append("")
            lines.append("  ML TRAINING")
            add("Push urgency datasets (ingest+clean)", do_push_urgency_datasets)
            add("Push CAE datasets (ingest+clean)", do_push_adaptation_datasets)
            add("Train urgency model", do_train_urgency)
            add("Train CAE models", do_train_cae)
            add("Train all (urgency+CAE+KB)", do_train_all_models)
        elif role == ROLE_JOURNALIST:
            add("Add news", do_add_news)
            add("Add article", do_add_article)
            add("View content by ID", do_view_content)
            add("List content", do_list_content)
            add("List news", do_list_news)
        elif role == ROLE_AUDIENCE_ANALYST:
            add("Add story pitch", do_add_pitch)
            add("Add category", do_add_category)
            add("List content", do_list_content)
        elif role == ROLE_EDITOR:
            add("View content by ID", do_view_content)
            add("List content", do_list_content)
            add("List news", do_list_news)
            if has_capability(role, CAP_PITCH_REVIEW):
                add("Update content status (review)", do_update_content_status)
        elif role == ROLE_PUBLISHER:
            add("View content by ID", do_view_content)
            add("List content", do_list_content)
            add("List news", do_list_news)
            add("Update content status (publish)", do_update_content_status)
        elif role == ROLE_NEWSROOM_MANAGER:
            add("Add user", do_add_user)
            add("Reset user password", do_admin_reset_password)
            add("Add category", do_add_category)
            add("View content by ID", do_view_content)
            add("List content", do_list_content)
            add("List news", do_list_news)
            add("Update content status", do_update_content_status)
        elif role == ROLE_ADAPTATION_EDITOR:
            add("View content by ID", do_view_content)
            add("List content", do_list_content)
            add("List news", do_list_news)
        else:
            lines.append("  (no desk actions configured for this role)")

    lines.append("")
    lines.append("  SYSTEM")
    add("DB status", do_status)

    lines.append("")
    lines.append("  0) Exit")
    lines.append("=" * 56)
    lines.append("")
    return "\n".join(lines), actions


def interactive() -> int:
    info("NewsMind console ready. Login to unlock your role menu.")
    while True:
        user = _current_user()
        menu_text, actions = _build_menu(user)
        print(menu_text)
        try:
            choice = input("Choose option: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            return 0
        if choice == "0" or is_cancel(choice):
            print("Bye.")
            return 0
        action = actions.get(choice)
        if action is None:
            error("Invalid option.")
            continue
        info("Tip: q / exit cancels this step | Ctrl+C cancels a running step")
        try:
            action()
        except UserCancelled:
            info("Action cancelled. Back to menu.")
        except KeyboardInterrupt:
            print("\nCancelled. Back to menu.")
        except Exception as exc:  # noqa: BLE001
            _handle(exc)
        try:
            nxt = input("\nPress Enter to continue: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            return 0
        if is_cancel(nxt) or nxt == "0":
            print("Bye.")
            return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NewsMind console application")
    parser.add_argument("--menu", action="store_true", help="Open interactive console menu")
    parser.add_argument("--init-db", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--logout", action="store_true")
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--list-csv", action="store_true")
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--ingest-new", action="store_true")
    parser.add_argument("--ingest-file", default="", help="Relative path under data/raw")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--ingest-clean", action="store_true")
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--pipeline", action="store_true")
    parser.add_argument("--pipeline-new", action="store_true")
    parser.add_argument("--pipeline-file", default="", help="Relative path under data/raw")
    parser.add_argument("--list-reports", action="store_true")
    parser.add_argument("--view-report", type=int, default=0)
    args = parser.parse_args()

    if len(sys.argv) == 1 or args.menu:
        return interactive()

    if args.init_db:
        return do_init_db()
    if args.status:
        return do_status()
    if args.login:
        return do_login(args.username, args.password)
    if args.logout:
        return do_logout()
    if args.list_csv:
        return do_list_csv_files()
    if args.ingest_file:
        return _run_admin(lambda: admin.ingest_file(args.ingest_file), title=f"Ingest File — {args.ingest_file}")
    if args.ingest_new:
        return do_ingest_new()
    if args.ingest:
        return do_ingest()
    if args.clean:
        return do_clean()
    if args.ingest_clean:
        return do_ingest_and_clean()
    if args.persist:
        return do_persist()
    if args.pipeline_file:
        return _run_admin(lambda: admin.pipeline_file(args.pipeline_file), title=f"Pipeline File — {args.pipeline_file}")
    if args.pipeline_new:
        return do_pipeline_new()
    if args.pipeline:
        return do_pipeline()
    if args.list_reports:
        return do_list_reports()
    if args.view_report:
        try:
            payload = admin.view_report(args.view_report)
            row = payload["report"]
            print(json.dumps(row, indent=2, default=str))
            return 0
        except Exception as exc:  # noqa: BLE001
            return _handle(exc)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
