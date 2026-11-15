"""Fail if any tracked file mentions a word the project keeps out of its vocabulary.

The list is read from scripts/forbidden_words.txt, one word per line, so the words
themselves do not appear in this script.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS = [w.strip() for w in (ROOT / "scripts" / "forbidden_words.txt").read_text().splitlines() if w.strip()]
SKIP = {"scripts/forbidden_words.txt", "uv.lock"}
files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
pattern = re.compile("|".join(re.escape(w) for w in WORDS), re.I)
bad = 0
for rel in files:
    if rel in SKIP:
        continue
    p = ROOT / rel
    if not p.is_file():
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for n, line in enumerate(text.splitlines(), start=1):
        if pattern.search(line):
            print(f"{rel}:{n}: {line.strip()[:100]}")
            bad += 1
sys.exit(1 if bad else 0)
