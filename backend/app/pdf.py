import io

from slugify import slugify
from weasyprint import HTML

from app.cv_data import CV


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
  size: A4;
  margin: 1in;
}}
body {{
  font-family: "DejaVu Serif", "Times New Roman", serif;
  font-size: 11pt;
  line-height: 1.5;
  color: #111;
}}
.header {{
  margin-bottom: 1.25em;
  border-bottom: 1px solid #888;
  padding-bottom: 0.6em;
}}
.name {{
  font-size: 16pt;
  font-weight: bold;
  margin: 0 0 0.2em 0;
}}
.contact {{
  font-size: 10pt;
  color: #444;
}}
.body {{
  white-space: pre-wrap;
}}
</style>
</head>
<body>
<div class="header">
  <div class="name">{name}</div>
  <div class="contact">{contact}</div>
</div>
<div class="body">{letter}</div>
</body>
</html>
"""


def _format_contact(personal: dict) -> str:
    """Render email · phone · links into one line.

    Accepts two shapes for `personal["links"]`:
      - dict:   {label: url | None, ...}     (e.g. {"linkedin": "https://..."})
      - list:   [{"label": ..., "url": ...}, ...]  OR  ["raw string", ...]
    """
    parts: list[str] = []
    if personal.get("email"):
        parts.append(str(personal["email"]))
    if personal.get("phone"):
        parts.append(str(personal["phone"]))

    links = personal.get("links")
    if isinstance(links, dict):
        for label, url in links.items():
            if url and isinstance(url, str):
                parts.append(f"{label}: {url}")
    elif isinstance(links, list):
        for link in links:
            if isinstance(link, dict):
                label = link.get("label") or link.get("url") or ""
                url = link.get("url") or link.get("label") or ""
                if label and url:
                    parts.append(f"{label}: {url}")
            elif isinstance(link, str):
                parts.append(link)
    return " · ".join(parts)


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )


def render_pdf(letter_content: str) -> tuple[bytes, str]:
    """Return (pdf_bytes, base_name_for_filename)."""
    personal = CV.get("personal_info", {})
    name = str(personal.get("name") or "")
    contact = _format_contact(personal)
    html = HTML_TEMPLATE.format(
        name=_escape(name),
        contact=_escape(contact),
        letter=_escape(letter_content),
    )
    buf = io.BytesIO()
    HTML(string=html).write_pdf(target=buf)
    return buf.getvalue(), name or "cover-letter"


def pdf_filename(company_name: str, job_title: str) -> str:
    base = f"cover-letter_{company_name}_{job_title}"
    return f"{slugify(base)}.pdf"
