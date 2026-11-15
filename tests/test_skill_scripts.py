"""The skill's standard-library scripts must agree with the engine."""

import json
import subprocess
import sys
from pathlib import Path

from agent_arb.models import Decision, Scope
from agent_arb.rules import RuleSet, load_builtin_packs

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "agent-arb"


def _sync() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_packs.py")], check=True, capture_output=True)


def test_select_rules_script_matches_engine(tmp_path: Path) -> None:
    _sync()
    d = Decision(
        id="D1",
        title="t",
        section_ref="S1",
        scope=Scope.ARCHITECTURE,
        tags=["auth", "tls", "messaging"],
        data_classes=["cardholder-data"],
    )
    dj = tmp_path / "d.json"
    dj.write_text(d.model_dump_json())
    out = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "select_rules.py"), "--decision", str(dj), "--tier", "1"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    script_ids = {r["id"] for r in json.loads(out)["rules"]}
    engine_ids = {r.id for r in RuleSet(load_builtin_packs()).select(d, tier=1)}
    assert script_ids == engine_ids


def test_verify_quotes_script(tmp_path: Path) -> None:
    section = tmp_path / "s.txt"
    section.write_text("The cluster runs in two availability zones with synchronous replication.")
    findings = tmp_path / "f.json"
    findings.write_text(
        json.dumps(
            {
                "findings": [
                    {"rule_id": "A", "verdict": "fail", "quote": "runs in two availability zones"},
                    {"rule_id": "B", "verdict": "fail", "quote": "runs in three zones"},
                ]
            }
        )
    )
    out = json.loads(
        subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts" / "verify_quotes.py"),
                "--findings",
                str(findings),
                "--section-text",
                str(section),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert [f["rule_id"] for f in out["kept"]] == ["A"]
    assert [f["rule_id"] for f in out["dropped"]] == ["B"]


def test_split_sections_script_matches_engine() -> None:
    from agent_arb.ingest import read_document, split_sections

    doc = ROOT / "examples" / "orders-service-design.md"
    out = json.loads(
        subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "split_sections.py"), str(doc)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    engine = split_sections(read_document(doc))
    assert [(s["ref"], s["heading"], s["start_line"], s["end_line"]) for s in out] == [
        (s.ref, s.heading, s.start_line, s.end_line) for s in engine
    ]
