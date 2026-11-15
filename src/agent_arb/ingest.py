"""Split a design document into sections by heading, locally.

Markdown is the native format. PDF and Word are converted to Markdown-like
text first, best effort, with page markers kept so a citation can name a page.
No model is involved at any point.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import Section

HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        return _pdf_to_text(path)
    if suffix == ".docx":
        return _docx_to_text(path)
    raise ValueError(f"unsupported document type: {path.suffix}")


def _pdf_to_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for n, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        parts.append(f"\n<!-- page {n} -->\n{text}")
    return _promote_headings("\n".join(parts))


def _docx_to_text(path: Path) -> str:
    # python-docx is optional; a .docx is a zip of XML, and paragraphs are enough here.
    import zipfile
    from xml.etree import ElementTree as ET

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    lines: list[str] = []
    for p in root.iterfind(".//w:p", ns):
        style = p.find("w:pPr/w:pStyle", ns)
        text = "".join(t.text or "" for t in p.iterfind(".//w:t", ns)).strip()
        if not text:
            continue
        sval = style.get(f"{{{ns['w']}}}val", "") if style is not None else ""
        m = re.match(r"Heading(\d)", sval)
        if m:
            lines.append("#" * int(m.group(1)) + " " + text)
        else:
            lines.append(text)
    return "\n".join(lines)


def _promote_headings(text: str) -> str:
    """Turn short, numbered or title-case lines into Markdown headings."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if (
            s
            and len(s) < 80
            and not s.endswith(".")
            and (re.match(r"^\d+(\.\d+)*\s+\S", s) or (s.istitle() and len(s.split()) <= 8))
        ):
            depth = s.count(".", 0, s.find(" ")) + 1 if s[0].isdigit() else 2
            out.append("#" * min(depth, 4) + " " + s)
        else:
            out.append(line)
    return "\n".join(out)


def split_sections(text: str) -> list[Section]:
    """One section per heading. Text before the first heading becomes the preamble."""
    lines = text.splitlines()
    sections: list[Section] = []
    current_start = 0
    current_heading = "Preamble"
    current_level = 0
    counter = 0

    def close(end_line: int) -> None:
        nonlocal counter
        body = "\n".join(lines[current_start:end_line]).strip()
        if not body and current_heading == "Preamble":
            return
        counter += 1
        sections.append(
            Section(
                ref=f"S{counter}",
                heading=current_heading,
                level=current_level,
                start_line=current_start + 1,
                end_line=end_line,
                text=body,
            )
        )

    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if m:
            close(i)
            current_start = i
            current_heading = m.group(2)
            current_level = len(m.group(1))
    close(len(lines))
    return sections


def outline(sections: list[Section], first_chars: int = 240) -> str:
    """A compact view of the document for document-target rules: headings plus the opening of each section."""
    rows = []
    for s in sections:
        body = s.text.split("\n", 1)[1] if "\n" in s.text else ""
        snippet = re.sub(r"\s+", " ", body)[:first_chars]
        rows.append(f"{'#' * max(s.level, 1)} {s.heading} [{s.ref}]\n{snippet}")
    return "\n\n".join(rows)
