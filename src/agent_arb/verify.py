"""Keep only findings whose quote is really in the text.

A quote is accepted verbatim, or repaired to the single sentence of the text it
clearly paraphrases when most of the quote's words occur in that sentence. A
repaired finding carries the real sentence, never the model's wording. Anything
else is dropped.
"""

from __future__ import annotations

import re

from .models import Finding

REPAIR_THRESHOLD = 0.75
REPAIR_MIN_WORDS = 5
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"[a-z0-9][a-z0-9%-]*(?:\.[a-z0-9%-]+)*")


def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("“", '"').replace("”", '"').replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_in(quote: str, text: str) -> bool:
    q = _norm(quote)
    if len(q) < 8:
        return False
    return q in _norm(text)


def repair_quote(quote: str, text: str, threshold: float = REPAIR_THRESHOLD) -> str | None:
    """The sentence of ``text`` that contains most of the quote's words, or None."""
    qwords = set(_WORD.findall(_norm(quote)))
    if len(qwords) < REPAIR_MIN_WORDS:
        return None
    numbers = {w for w in qwords if any(ch.isdigit() for ch in w)}
    best, best_score = None, 0.0
    for sentence in _SENTENCE.split(text):
        s = sentence.strip()
        if len(s) < 8:
            continue
        swords = set(_WORD.findall(_norm(s)))
        if numbers - swords:
            continue  # a number in the quote that the sentence lacks is a contradiction, not a paraphrase
        score = len(qwords & swords) / len(qwords)
        if score > best_score:
            best, best_score = s, score
    return best if best is not None and best_score >= threshold else None


def resolve_quote(quote: str, text: str) -> tuple[str | None, bool]:
    """(quote to keep, repaired?) or (None, False) when the quote cannot be grounded."""
    if quote_in(quote, text):
        return quote, False
    repaired = repair_quote(quote, text)
    return (repaired, True) if repaired else (None, False)


def verify_findings(findings: list[Finding], text: str) -> tuple[list[Finding], list[Finding]]:
    kept: list[Finding] = []
    dropped: list[Finding] = []
    for f in findings:
        if f.verdict == "unclear" and not f.quote:
            f.verified = True
            kept.append(f)
            continue
        quote, repaired = resolve_quote(f.quote, text)
        if quote is None:
            f.verified = False
            dropped.append(f)
            continue
        if repaired:
            f.quote = quote
            f.explanation = (f.explanation + " [quote matched to the nearest sentence]").strip()
        f.verified = True
        kept.append(f)
    return kept, dropped
