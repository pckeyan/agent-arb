"""Copy the rule packs into the skill folder as JSON, so the skill's standard-library scripts can read them.

Run before a release. The skill never reads YAML.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_arb.models import Pack  # noqa: E402
from agent_arb.rules import TAG_FAMILIES, load_pack  # noqa: E402

SRC = ROOT / "rules"
DST = ROOT / "skills" / "agent-arb" / "rules"
DST.mkdir(parents=True, exist_ok=True)
for old in DST.glob("*.json"):
    old.unlink()
count = 0
for path in sorted(SRC.rglob("*.yaml")):
    if path.name in {"canon.yaml", "tiers.yaml"}:
        continue
    pack: Pack = load_pack(path)
    out = DST / f"{pack.name}.json"
    out.write_text(json.dumps(pack.model_dump(mode="json"), indent=1) + "\n", encoding="utf-8")
    count += len(pack.rules)
tiers = yaml.safe_load((SRC / "tiers.yaml").read_text(encoding="utf-8"))
(DST / "tiers.json").write_text(json.dumps(tiers, indent=1) + "\n", encoding="utf-8")
(DST / "tags.json").write_text(json.dumps({"families": TAG_FAMILIES}, indent=1) + "\n", encoding="utf-8")
REFS = ROOT / "skills" / "agent-arb" / "references"
for name in ("decisions", "review", "document"):
    (REFS / f"{name}-prompt.md").write_text(
        (ROOT / "src" / "agent_arb" / "prompts" / f"{name}.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
print(f"synced {count} rules and 3 prompts into the skill")
