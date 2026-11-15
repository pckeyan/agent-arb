"""Write the JSON schemas under spec/ from the Pydantic models. Run after changing models.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_arb.models import Decision, Finding, ManifestEntry, Pack, Record, Rule  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "spec"
OUT.mkdir(exist_ok=True)
for name, model in {
    "rule": Rule,
    "pack": Pack,
    "decision": Decision,
    "finding": Finding,
    "record": Record,
    "manifest-entry": ManifestEntry,
}.items():
    path = OUT / f"{name}.schema.json"
    path.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(OUT.parent)}")
