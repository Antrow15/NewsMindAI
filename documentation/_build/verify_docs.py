from pathlib import Path
from docx import Document

docx_path = Path(r"g:\NewsMind AI\NewsMindAI V2\documentation\Complete_Application_Learning_Guide.docx")
pdf_path = Path(r"g:\NewsMind AI\NewsMindAI V2\documentation\Complete_Application_Learning_Guide.pdf")

d = Document(str(docx_path))
heads = [para.text for para in d.paragraphs if para.style.name.startswith("Heading")]
print("docx_ok", docx_path.exists(), "size", docx_path.stat().st_size)
print("pdf_ok", pdf_path.exists(), "size", pdf_path.stat().st_size)
print("paragraphs", len(d.paragraphs))
print("tables", len(d.tables))
print("heading_count", len(heads))
print("--- headings sample ---")
for h in heads[:50]:
    print(h)
need = [
    "1. Learning Goals",
    "2. Complete Application Architecture",
    "6. Every API Endpoint",
    "7. Database",
    "14. Code-Level",
    "14B. Expanded",
    "Appendix D",
    "Appendix E",
]
text = "\n".join(heads)
for n in need:
    print(("OK" if n in text else "MISSING"), n)
print("last_headings:")
for h in heads[-15:]:
    print(h)
