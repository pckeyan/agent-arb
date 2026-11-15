"""Append-only log of what each prompt carried."""

from __future__ import annotations

import json
from pathlib import Path

from .models import ManifestEntry


class Manifest:
    def __init__(self, path: Path):
        self.path = path
        self.entries: list[ManifestEntry] = []

    def add(self, entry: ManifestEntry) -> None:
        self.entries.append(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry.model_dump()) + "\n")
