"""Write examples/seeds/acme-platform-standards.pdf from the Markdown seed, with no PDF library.

A minimal PDF with Helvetica text that pypdf can extract. Run once; the output is committed.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "examples" / "seeds" / "acme-platform-standards.md"
DST = ROOT / "examples" / "seeds" / "acme-platform-standards.pdf"


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


lines = [ln.lstrip("#").strip() if ln.startswith("#") else ln for ln in SRC.read_text().splitlines()]
content = ["BT", "/F1 11 Tf", "14 TL", "50 780 Td"]
for ln in lines:
    content.append(f"({esc(ln)}) Tj T*")
content.append("ET")
stream = "\n".join(content).encode("latin-1")
objs = [
    b"<< /Type /Catalog /Pages 2 0 R >>",
    b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
]
out = bytearray(b"%PDF-1.4\n")
offsets = []
for i, body in enumerate(objs, start=1):
    offsets.append(len(out))
    out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
xref = len(out)
out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
for off in offsets:
    out += f"{off:010d} 00000 n \n".encode()
out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
DST.write_bytes(bytes(out))
print(f"wrote {DST.relative_to(ROOT)} ({len(out)} bytes)")
