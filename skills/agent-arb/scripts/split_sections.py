#!/usr/bin/env python3
"""List a Markdown document's sections with line ranges. Standard library only."""

import json
import re
import sys

HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def main(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    sections = []
    start, heading, level = 0, "Preamble", 0
    n = 0

    def close(end):
        nonlocal n
        body = "\n".join(lines[start:end]).strip()
        if not body and heading == "Preamble":
            return
        n += 1
        sections.append({"ref": f"S{n}", "heading": heading, "level": level, "start_line": start + 1, "end_line": end})

    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if m:
            close(i)
            start, heading, level = i, m.group(2), len(m.group(1))
    close(len(lines))
    print(json.dumps(sections, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
