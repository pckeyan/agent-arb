from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from agent_arb.llm import FakeModel

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "orders-service-design.md"


def _first_sentence(text: str) -> str:
    body = text.split("\n", 1)[1] if "\n" in text else text
    for line in body.splitlines():
        line = line.strip()
        if line:
            m = re.match(r"(.+?\.)(\s|$)", line)
            return m.group(1) if m else line
    return ""


def scripted_responder(system: str, user: str) -> dict[str, Any]:
    """A fake model that proposes one decision per section and passes every rule with a real quote."""
    if "extracting architecture decisions" in system:
        head, _, body = user.partition("\n\n")
        heading = head.split(":", 1)[1].strip() if ":" in head else head
        if heading in {"Goals and non-goals", "Open questions", "Context"} or not body.strip():
            return {"decisions": []}
        tags = ["data"] if "database" in body.lower() else []
        if "mutual tls" in body.lower():
            tags += ["auth", "tls", "identity", "integration"]
        if "card" in body.lower():
            tags += ["security", "data", "pci"]
        if "slo" in body.lower() or "p99" in body.lower():
            tags += ["observability", "latency", "slo", "alerting"]
        if "event" in body.lower():
            tags += ["messaging", "integration"]
        return {
            "decisions": [
                {
                    "title": f"Decision in {heading}",
                    "scope": "architecture",
                    "context": "from the text",
                    "options": [{"name": "alternative", "tradeoff": "worse"}],
                    "chosen": "the described approach",
                    "implications": "",
                    "evidence_quote": _first_sentence(body),
                    "tags": tags,
                    "data_classes": ["cardholder-data"] if "card" in body.lower() else [],
                }
            ]
        }
    if "review ONE decision" in system or "document OUTLINE" in system:
        rule_ids = re.findall(r"^- ([A-Z0-9-]+) \[", user.split("RULES:")[-1], re.M)
        text = user.split("SECTION TEXT")[-1] if "SECTION TEXT" in user else user.split("DOCUMENT OUTLINE:")[-1]
        quote = _first_sentence(text) if "SECTION TEXT" in user else text.strip().splitlines()[0]
        return {"findings": [{"rule_id": r, "verdict": "pass", "quote": quote, "explanation": "ok"} for r in rule_ids]}
    return {}


@pytest.fixture
def fake_model() -> FakeModel:
    return FakeModel(scripted_responder)


@pytest.fixture
def example_doc() -> Path:
    return EXAMPLE


def load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))
