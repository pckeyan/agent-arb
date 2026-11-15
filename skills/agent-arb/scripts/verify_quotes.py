#!/usr/bin/env python3
"""Keep only findings whose quote is really in the text. Standard library only.

A quote is accepted verbatim, or repaired to the single sentence it clearly paraphrases
when at least 75 percent of its words occur in that sentence, it has at least five words,
and every number in it appears in that sentence. Repaired findings carry
the real sentence and a note. A quote matching nothing is dropped with its finding. A failure with no quote is kept but
marked unverified; a pass with no quote is dropped.

Usage: verify_quotes.py --findings findings.json --section-text section.txt
Prints {"kept": [...], "dropped": [...]} and rewrites findings.json with the kept findings.
"""

import argparse
import json
import re

SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
WORD = re.compile(r"[a-z0-9][a-z0-9%-]*(?:\.[a-z0-9%-]+)*")


def norm(s):
    s = s.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2014", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def repair(quote, text):
    qwords = set(WORD.findall(norm(quote)))
    if len(qwords) < 5:
        return None
    numbers = {w for w in qwords if any(ch.isdigit() for ch in w)}
    best, score = None, 0.0
    for sentence in SENTENCE.split(text):
        s = sentence.strip()
        if len(s) < 8:
            continue
        swords = set(WORD.findall(norm(s)))
        if numbers - swords:
            continue
        sc = len(qwords & swords) / len(qwords)
        if sc > score:
            best, score = s, sc
    return best if best is not None and score >= 0.75 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--findings", required=True)
    ap.add_argument("--section-text", required=True)
    a = ap.parse_args()
    with open(a.findings, encoding="utf-8") as f:
        data = json.load(f)
    findings = data["findings"] if isinstance(data, dict) else data
    with open(a.section_text, encoding="utf-8") as f:
        raw = f.read()
    text = norm(raw)
    kept, dropped = [], []
    for fnd in findings:
        q = norm(fnd.get("quote", ""))
        if not q:
            if fnd.get("verdict") == "pass":
                fnd["verified"] = False
                dropped.append(fnd)
                continue
            fnd["verified"] = False
            if fnd.get("verdict") == "fail":
                fnd["explanation"] = (
                    fnd.get("explanation", "") + " [no quote offered; the model reports the information is absent]"
                ).strip()
            kept.append(fnd)
            continue
        if len(q) >= 8 and q in text:
            fnd["verified"] = True
            kept.append(fnd)
            continue
        fixed = repair(fnd.get("quote", ""), raw)
        if fixed:
            fnd["quote"] = fixed
            fnd["explanation"] = (fnd.get("explanation", "") + " [quote matched to the nearest sentence]").strip()
            fnd["verified"] = True
            kept.append(fnd)
        else:
            fnd["verified"] = False
            dropped.append(fnd)
    with open(a.findings, "w", encoding="utf-8") as f:
        json.dump({"findings": kept}, f, indent=1)
    print(json.dumps({"kept": kept, "dropped": dropped}, indent=1))


if __name__ == "__main__":
    main()
