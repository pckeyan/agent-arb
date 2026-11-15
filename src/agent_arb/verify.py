"""Drop any finding whose quote is not in the text it claims to quote."""

from __future__ import annotations

import re

from .models import Finding


def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("“", '"').replace("”", '"').replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_in(quote: str, text: str) -> bool:
    q = _norm(quote)
    if len(q) < 8:
        return False
    return q in _norm(text)


def verify_findings(findings: list[Finding], text: str) -> tuple[list[Finding], list[Finding]]:
    kept: list[Finding] = []
    dropped: list[Finding] = []
    for f in findings:
        if f.verdict == "unclear" and not f.quote or quote_in(f.quote, text):
            f.verified = True
            kept.append(f)
        else:
            f.verified = False
            dropped.append(f)
    return kept, dropped
