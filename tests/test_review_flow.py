import json
from pathlib import Path

from agent_arb.cli import run_review
from agent_arb.llm import FakeModel
from agent_arb.rules import load_builtin_packs, load_pack

ROOT = Path(__file__).resolve().parents[1]


def test_end_to_end_with_fake_model(example_doc: Path, fake_model: FakeModel, tmp_path: Path) -> None:
    packs = load_builtin_packs() + [load_pack(ROOT / "examples" / "seeds" / "acme-overrides.yaml")]
    record = run_review(example_doc, packs, fake_model, tmp_path, tier=1, interactive=False, challenge=False)
    assert record.decisions, "expected decisions"
    assert all(d.confirmed for d in record.decisions)
    assert record.findings and all(f.verified for f in record.findings)
    pci = [f for f in record.findings if f.rule_id.startswith("IND-SEC-PCI")]
    assert pci, "PCI rules should fire on the payment decision"
    assert any(c.framework == "PCI-DSS-v4.0.1" for c in record.compliance)
    assert any("p99" in s for s in record.service_levels)
    md = (tmp_path / "orders-service-design.record.md").read_text()
    assert "Compliance traceability" in md and "not an assessment" in md
    js = json.loads((tmp_path / "orders-service-design.record.json").read_text())
    assert js["engine"] == "agent-arb"
    manifest = (tmp_path / "orders-service-design.manifest.jsonl").read_text().splitlines()
    assert manifest, "manifest should be written"
    for line in manifest:
        entry = json.loads(line)
        assert len(entry["sections"]) <= 1, "a prompt never carries more than one section"


def test_data_boundary_one_section_per_prompt(example_doc: Path, fake_model: FakeModel, tmp_path: Path) -> None:
    run_review(example_doc, load_builtin_packs(), fake_model, tmp_path, tier=2, interactive=False, challenge=False)
    from agent_arb.ingest import read_document, split_sections

    bodies = [
        s.text.split("\n", 1)[1].strip()[:120] for s in split_sections(read_document(example_doc)) if "\n" in s.text
    ]
    for _system, user in fake_model.calls:
        if "DOCUMENT OUTLINE" in user:
            continue  # the outline carries a snippet of every section by design
        present = sum(1 for b in bodies if b and b in user)
        assert present <= 1, "a prompt may carry at most one section's text"
