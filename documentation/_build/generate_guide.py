"""Generate Complete_Application_Learning_Guide.docx (+ PDF) for NewsMindAI V2."""

from __future__ import annotations

import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
DOC_ROOT = BUILD.parent
OUT_DOCX = DOC_ROOT / "Complete_Application_Learning_Guide.docx"
OUT_PDF = DOC_ROOT / "Complete_Application_Learning_Guide.pdf"

sys.path.insert(0, str(BUILD))

import docx_helpers as H  # noqa: E402
from auto_catalog import add_catalog_chapter  # noqa: E402
from chapters_part1 import chapter_1, chapter_2, chapter_3, chapter_4, chapter_5  # noqa: E402
from chapters_part2 import (  # noqa: E402
    chapter_6,
    chapter_7,
    chapter_8,
    chapter_9,
    chapter_10,
    chapter_11,
)
from chapters_deep_dive import chapter_deep_dive  # noqa: E402
from chapters_part3 import (  # noqa: E402
    appendices,
    chapter_12,
    chapter_13,
    chapter_14,
    chapter_15,
    chapter_16,
    chapter_17,
    chapter_18,
)


def build_docx() -> Path:
    doc = H.setup_document()
    H.cover_page(doc)
    H.toc_placeholder(doc)

    chapter_1(doc)
    chapter_2(doc)
    chapter_3(doc)
    chapter_4(doc)
    chapter_5(doc)
    chapter_6(doc)
    chapter_7(doc)
    chapter_8(doc)
    chapter_9(doc)
    chapter_10(doc)
    chapter_11(doc)
    chapter_12(doc)
    chapter_13(doc)
    chapter_14(doc)
    chapter_deep_dive(doc)
    chapter_15(doc)
    chapter_16(doc)
    chapter_17(doc)
    chapter_18(doc)
    appendices(doc)
    add_catalog_chapter(doc, H)

    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    doc.save(OUT_DOCX)
    return OUT_DOCX


def build_pdf_from_text() -> Path | None:
    """Create a PDF companion via reportlab (structured digest + TOC + key chapters)."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            PageBreak,
            Paragraph,
            Preformatted,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        print("reportlab not available; skipping PDF")
        return None

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontSize=26,
            textColor=colors.HexColor("#1A2B4A"),
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyJust",
            parent=styles["BodyText"],
            alignment=TA_JUSTIFY,
            fontSize=10,
            leading=14,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeBlock",
            parent=styles["Code"],
            fontSize=8,
            leading=10,
            backColor=colors.HexColor("#F4F6F8"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1Custom",
            parent=styles["Heading1"],
            textColor=colors.HexColor("#1A2B4A"),
            fontSize=16,
            spaceBefore=16,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2Custom",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#2C5F8A"),
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
        )
    )

    story = []
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("NewsMind AI V2", styles["CoverTitle"]))
    story.append(
        Paragraph(
            "Complete Application Learning Guide (PDF Companion)",
            styles["Heading2"],
        )
    )
    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            "This PDF is a portable companion to "
            "<b>Complete_Application_Learning_Guide.docx</b>. "
            "The Word document is the primary deliverable with the full auto-generated "
            "source catalog, detailed endpoint tables, and file-by-file appendix. "
            "Both are generated from the same analysis of the NewsMindAI V2 repository.",
            styles["BodyJust"],
        )
    )
    story.append(PageBreak())

    def h1(t):
        story.append(Paragraph(t, styles["H1Custom"]))

    def h2(t):
        story.append(Paragraph(t, styles["H2Custom"]))

    def body(t):
        story.append(Paragraph(t.replace("\n", "<br/>"), styles["BodyJust"]))

    def code(t):
        story.append(Preformatted(t, styles["CodeBlock"]))
        story.append(Spacer(1, 6))

    h1("1. Learning Goals")
    body(
        "NewsMind AI V2 is a modular-monolith newsroom backend: FastAPI role APIs plus "
        "console CLI, PostgreSQL persistence, CSV ETL cleaners, and ML helpers for editor "
        "urgency, CAE adaptation, TF-IDF relevancy, and AIA heuristics."
    )
    body(
        "<b>After this guide you should:</b> explain architecture; trace any endpoint; "
        "modify services/DAOs safely; debug 401/403/422/503; retrain models; rebuild a similar system."
    )

    h1("2. Architecture")
    body(
        "Layers: api/ → modules/ → services/ → repository/ → dao/ → entities/ → PostgreSQL. "
        "Cross-cutting: config/, utils/, cleaners/, ml/. Clients: /docs, /easy, app.py."
    )
    code(
        "Client → Router → Bearer deps → Pydantic → capability gate\n"
        "  → Module/Service → Repository/DAO/ML → Postgres → JSON"
    )

    h1("3. Roles & Capabilities")
    data = [
        ["Role", "Key capabilities"],
        ["administrator", "all (ingest…manage_users, journalist_tools)"],
        ["journalist", "ingest, clean, persist, pipeline, journalist_tools"],
        ["editor", "pitch_review, content_review, assign, analytics"],
        ["publisher", "publish"],
        ["content_adaptation_editor", "adapt"],
        ["audience_insight_analyst", "ingest, clean, analytics"],
        ["newsroom_manager", "review, assign, adapt, publish, analytics, manage_users"],
    ]
    t = Table(data, colWidths=[2.2 * inch, 4.3 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A2B4A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    h1("4. Endpoint Map (summary)")
    body(
        "/auth (login/logout/password) · /journalist (tools+desk) · /aia · /cae · "
        "/publisher · /editor · /manager · /admin (ETL+users+categories) · GET /easy"
    )
    body(
        "Full per-endpoint documentation with request/response examples lives in the DOCX "
        "Chapter 6 and Appendix E (auto-extracted routes)."
    )

    h1("5. Database")
    body(
        "Bootstrap: database/newsmind.sql (destructive public schema reset) + seed_demo_users. "
        "Core: employee→users→desk profiles; content↔article|news; evidence; story_pitch; "
        "publication; adaptation_*; raw_ingest; ml_train_*."
    )
    body("Statuses: draft → submitted → approved|rejected|rework → published.")

    h1("6. ETL")
    code(
        "data/raw/*.csv → IngestionService (hash skip)\n"
        "→ CleaningOrchestrator: Text→Null→Duplicate→Schema\n"
        "→ PersistenceService → content (+ article|news) / rejected raw_ingest\n"
        "→ ReportService → cleaning_report"
    )

    h1("7. ML")
    body(
        "<b>Trained:</b> editor_queue_urgency (XGBoost) and CAE sentence retention "
        "(LogisticRegression). <b>Heuristic:</b> AIA engagement/interest/trend. "
        "<b>Unsupervised similarity:</b> TF-IDF relevancy/duplicates over published content."
    )

    h1("8. Auth")
    body(
        "PBKDF2-HMAC-SHA256 password hashes (salt$digest). Auth uses JWT HS256 access tokens "
        "(session_token field). NEWSROOM_JWT_SECRET is required in .env. Logout revokes jti "
        "in-process. CLI may store last JWT in logs/.session_token. TTL 12 hours."
    )

    h1("9. Validation & Errors")
    body(
        "Pydantic at HTTP edge; utils.validators in services/cleaners. AppError hierarchy maps to "
        "401/403/404/400/503/500 via api/http_errors.py and main.py handlers. 422 for schema failures."
    )

    h1("10. Testing")
    body(
        "pytest + TestClient. Suites: auth password, journalist, aia, cae/publisher/editor/manager, "
        "integration pipeline, single-file ingest. db_ready skips without Postgres."
    )

    h1("11. Practical first hour")
    body(
        "1) Copy ENV.example → .env  2) pip install -r requirements.txt  3) python app.py --init-db  "
        "4) uvicorn api.main:app --reload  5) Open /easy, login as journalist, create news with evidence, "
        "submit; login editor approve; login publisher publish; login analyst open /aia/performance."
    )

    h1("12. Diagrams")
    body(
        "See documentation/diagrams/*.mmd (architecture, ETL, newsroom sequence, ERD). "
        "Render with Mermaid."
    )

    h1("13. Assessment reminder")
    body(
        "Complete the checklist in DOCX Chapter 18. Prefer the Word document for the exhaustive "
        "file catalog and endpoint tables."
    )

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(inch, 0.6 * inch, "NewsMind AI V2 Learning Guide (PDF companion)")
        canvas.drawRightString(LETTER[0] - inch, 0.6 * inch, f"Page {doc_.page}")
        canvas.restoreState()

    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    pdf = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=LETTER,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        title="NewsMind AI V2 Complete Application Learning Guide",
        author="NewsMind Documentation Generator",
    )
    pdf.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return OUT_PDF


def main() -> int:
    print("Building DOCX...")
    docx = build_docx()
    print(f"Wrote {docx} ({docx.stat().st_size:,} bytes)")
    print("Building PDF companion...")
    pdf = build_pdf_from_text()
    if pdf:
        print(f"Wrote {pdf} ({pdf.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
