"""The alignment page: actions, outcome and digital acceptance by date."""

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_arb.alignment import derive_actions, derive_outcome, sign
from agent_arb.cli import app, run_review
from agent_arb.llm import FakeModel
from agent_arb.models import Finding, Record, Severity
from agent_arb.record import render_markdown
from agent_arb.rules import load_builtin_packs


def _finding(rule: str, verdict: str, verified: bool, disposition: str = "open") -> Finding:
    return Finding(
        rule_id=rule,
        decision_id="D1",
        verdict=verdict,  # type: ignore[arg-type]
        severity=Severity.HIGH,
        verified=verified,
        disposition=disposition,  # type: ignore[arg-type]
    )


def test_actions_come_from_verified_or_dispositioned_failures_only() -> None:
    findings = [
        _finding("A", "fail", True),  # verified: action
        _finding("B", "fail", False),  # unverified and untouched: appendix only
        _finding("C", "fail", False, "accepted"),  # author accepted it: action
        _finding("D", "fail", True, "waived"),  # waived: never an action
        _finding("E", "pass", True),
        _finding("F", "fail", True, "disputed"),  # action, marked disputed
    ]
    actions = derive_actions(findings, {})
    assert [a.rule_id for a in actions] == ["A", "C", "F"]
    assert [a.id for a in actions] == ["A1", "A2", "A3"]
    assert actions[2].status == "disputed"


def test_sign_sets_date_and_derives_outcome() -> None:
    record = Record(engine="agent-arb", engine_version="0", model="m", document="d.md", tier=2)
    sign(record, "Ada", "Head of Platform", "approved", date="2026-11-16")
    assert record.approvals[0].date == "2026-11-16"
    assert record.outcome == "approved"
    sign(record, "Bob", "Security", "approved-with-conditions", note="rotate keys")
    assert record.outcome == "approved-with-conditions"
    sign(record, "Ada", "Head of Platform", "rejected", date="2026-11-17")  # same person again: one row, updated
    assert len(record.approvals) == 2 and record.outcome == "not-approved"
    record.approvals.clear()
    record.outcome = "pending"
    assert derive_outcome(record) == "pending"


def test_alignment_page_renders_first_with_date_column_and_no_signature() -> None:
    record = Record(engine="agent-arb", engine_version="0", model="m", document="d.md", tier=1)
    sign(record, "Ada", "Head of Platform", "approved", date="2026-11-16")
    md = render_markdown(record, {})
    assert md.index("## Alignment") < md.index("## Rule packs used")
    assert "| Name | Role | Decision | Date |" in md
    assert "Signature" not in md
    assert "| Ada | Head of Platform | approved | 2026-11-16 |" in md


def test_review_then_sign_command(example_doc: Path, fake_model: FakeModel, tmp_path: Path) -> None:
    record = run_review(
        example_doc,
        load_builtin_packs(),
        fake_model,
        tmp_path,
        tier=1,
        interactive=False,
        challenge=False,
        approvers=[("Ada", "Head of Platform")],
        document_version="v3",
    )
    assert record.document_hash and record.document_version == "v3"
    assert record.approvals[0].decision == "pending" and record.approvals[0].date == ""
    js = tmp_path / "orders-service-design.record.json"
    result = CliRunner().invoke(
        app,
        [
            "sign",
            str(js),
            "--name",
            "Ada",
            "--role",
            "Head of Platform",
            "--date",
            "2026-11-16",
            "--decision",
            "approved-with-conditions",
            "--condition",
            "Add a retry budget before launch",
        ],
    )
    assert result.exit_code == 0, result.output
    saved = json.loads(js.read_text())
    assert saved["outcome"] == "approved-with-conditions"
    assert saved["approvals"][0]["date"] == "2026-11-16"
    assert saved["conditions"] == ["Add a retry budget before launch"]
    md = (tmp_path / "orders-service-design.record.md").read_text()
    assert "approved with conditions | 2026-11-16" in md and "1. Add a retry budget before launch" in md
