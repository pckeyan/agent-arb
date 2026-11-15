#!/usr/bin/env python3
"""Keep only findings whose quote appears verbatim (whitespace-insensitive, case-insensitive) in the text.

Usage: verify_quotes.py --findings findings.json --section-text section.txt
Prints {"kept": [...], "dropped": [...]} and rewrites findings.json with the kept findings.
"""

import argparse
import json
import re


def norm(s):
    s = s.replace("’", "'").replace("“", '"').replace("”", '"').replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--findings", required=True)
    ap.add_argument("--section-text", required=True)
    a = ap.parse_args()
    with open(a.findings, encoding="utf-8") as f:
        data = json.load(f)
    findings = data["findings"] if isinstance(data, dict) else data
    text = norm(open(a.section_text, encoding="utf-8").read())
    kept, dropped = [], []
    for fnd in findings:
        q = norm(fnd.get("quote", ""))
        ok = (fnd.get("verdict") == "unclear" and not q) or (len(q) >= 8 and q in text)
        fnd["verified"] = bool(ok)
        (kept if ok else dropped).append(fnd)
    with open(a.findings, "w", encoding="utf-8") as f:
        json.dump({"findings": kept}, f, indent=1)
    print(json.dumps({"kept": kept, "dropped": dropped}, indent=1))


if __name__ == "__main__":
    main()
