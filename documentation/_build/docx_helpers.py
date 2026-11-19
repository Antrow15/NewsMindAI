"""Shared helpers for building the NewsMind V2 learning guide DOCX."""

from __future__ import annotations

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


NAVY = RGBColor(0x1A, 0x2B, 0x4A)
ACCENT = RGBColor(0x2C, 0x5F, 0x8A)
CODE_BG = RGBColor(0xF4, 0xF6, 0xF8)
MUTED = RGBColor(0x55, 0x55, 0x55)


def set_run_font(run, name="Calibri", size=11, bold=False, italic=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr)
    run._r.append(fld_char2)


def setup_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.9)
    section.bottom_margin = Inches(0.9)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run("NewsMind AI V2 — Complete Application Learning Guide")
    set_run_font(hr, size=9, italic=True, color=MUTED)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = fp.add_run("Page ")
    set_run_font(fr, size=9, color=MUTED)
    add_page_number(fp)
    fr2 = fp.add_run("  |  Confidential learning material — secrets redacted")
    set_run_font(fr2, size=9, color=MUTED)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

    for level, size in ((1, 18), (2, 14), (3, 12)):
        style = styles[f"Heading {level}"]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = NAVY if level == 1 else ACCENT
        style.paragraph_format.space_before = Pt(16 if level == 1 else 12)
        style.paragraph_format.space_after = Pt(8)

    if "CodeBlock" not in [s.name for s in styles]:
        code_style = styles.add_style("CodeBlock", WD_STYLE_TYPE.PARAGRAPH)
        code_style.font.name = "Consolas"
        code_style.font.size = Pt(8.5)
        code_style.paragraph_format.space_before = Pt(4)
        code_style.paragraph_format.space_after = Pt(4)
        code_style.paragraph_format.left_indent = Inches(0.15)

    return doc


def h(doc, text, level=1):
    return doc.add_heading(text, level=level)


def p(doc, text, *, bold=False, italic=False):
    para = doc.add_paragraph()
    run = para.add_run(text)
    set_run_font(run, bold=bold, italic=italic)
    return para


def bullet(doc, text, level=0):
    para = doc.add_paragraph(text, style="List Bullet")
    if level:
        para.paragraph_format.left_indent = Inches(0.25 * level)
    for run in para.runs:
        set_run_font(run)
    return para


def numbered(doc, text):
    para = doc.add_paragraph(text, style="List Number")
    for run in para.runs:
        set_run_font(run)
    return para


def code(doc, text: str):
    for line in text.splitlines() or [""]:
        para = doc.add_paragraph(style="CodeBlock")
        run = para.add_run(line if line else " ")
        set_run_font(run, name="Consolas", size=8.5)
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "F4F6F8")
        shading.set(qn("w:val"), "clear")
        para._p.get_or_add_pPr().append(shading)
    return None


def note(doc, text):
    para = doc.add_paragraph()
    run = para.add_run("Note: ")
    set_run_font(run, bold=True, italic=True, color=ACCENT)
    run2 = para.add_run(text)
    set_run_font(run2, italic=True, color=MUTED)
    return para


def table(doc, headers, rows):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, header in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(header)
        set_run_font(run, bold=True, size=10, color=RGBColor(0xFF, 0xFF, 0xFF))
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "1A2B4A")
        shading.set(qn("w:val"), "clear")
        cell._tePr = cell._tc.get_or_add_tcPr()
        cell._tc.get_or_add_tcPr().append(shading)
    for r_i, row in enumerate(rows):
        for c_i, val in enumerate(row):
            cell = t.rows[r_i + 1].cells[c_i]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(val))
            set_run_font(run, size=9)
    doc.add_paragraph()
    return t


def cover_page(doc):
    for _ in range(3):
        doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("NewsMind AI V2")
    set_run_font(r, name="Calibri", size=32, bold=True, color=NAVY)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("Complete Application Learning Guide")
    set_run_font(r, size=20, bold=True, color=ACCENT)

    line = doc.add_paragraph()
    line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = line.add_run("Technical Documentation • Architecture • Code Walkthrough • Exercises")
    set_run_font(r, size=11, italic=True, color=MUTED)

    doc.add_paragraph()
    meta = [
        ("Project", "NewsMindAI V2 — Console newsroom backend + FastAPI role APIs"),
        ("Version covered", "API 0.3.0 (api/main.py)"),
        ("Document type", "End-to-end learning guide (not a summary)"),
        ("Learning objective", "Understand, explain, modify, debug, and rebuild this application"),
        ("Secrets policy", "Passwords/API secrets shown as placeholders only"),
        ("Generated for", "Self-study of the existing V2 repository"),
    ]
    for k, v in meta:
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rk = para.add_run(f"{k}: ")
        set_run_font(rk, bold=True, size=11)
        rv = para.add_run(v)
        set_run_font(rv, size=11)

    doc.add_page_break()


def toc_placeholder(doc):
    h(doc, "Table of Contents", 1)
    p(
        doc,
        "This document uses Word heading styles (Heading 1–3). In Microsoft Word, "
        "place the cursor below this paragraph and use References → Table of Contents "
        "→ Automatic Table to insert a clickable TOC. Update the field (F9) after opening.",
        italic=True,
    )
    chapters = [
        "1. Learning Goals for This Application",
        "2. Complete Application Architecture",
        "3. Every Folder and File Explained",
        "4. Technical Concepts in Depth",
        "5. Keywords, Variables, Functions, and Classes",
        "6. Every API Endpoint in Detail",
        "7. Database Models, Schemas, and Queries",
        "8. Validation and Error Handling",
        "9. Complete End-to-End Application Flows",
        "10. Configuration and Environment Variables",
        "11. Frontend and Backend Integration",
        "12. External Libraries and Integrations",
        "13. Testing and Debugging",
        "14. Code-Level File-by-File Explanation",
        "14B. Expanded Source Walkthroughs (Actual Code)",
        "15. Design Decisions and Trade-offs",
        "16. Practical Learning Exercises",
        "17. Glossary of Technical Terms",
        "18. Final Knowledge Assessment",
        "Appendix A. Directory Tree",
        "Appendix B. Endpoint Quick Reference",
        "Appendix C. Diagram Index",
    ]
    for c in chapters:
        bullet(doc, c)
    doc.add_page_break()
