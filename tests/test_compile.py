from pathlib import Path

from agent_arb.compile import compile_seed, dump_pack
from agent_arb.models import Status
from agent_arb.rules import load_pack

ROOT = Path(__file__).resolve().parents[1]


def test_markdown_seed_compiles_to_draft_rules(tmp_path: Path) -> None:
    pack = compile_seed(ROOT / "examples" / "seeds" / "acme-platform-standards.md", "acme")
    assert len(pack.rules) >= 6
    assert all(r.status == Status.DRAFT for r in pack.rules)
    assert any("mutual TLS" in r.requirement for r in pack.rules)
    assert all(r.source.kind == "company" for r in pack.rules)
    out = tmp_path / "acme.yaml"
    dump_pack(pack, out)
    reloaded = load_pack(out)
    assert [r.id for r in reloaded.rules] == [r.id for r in pack.rules]


def test_yaml_seed_passthrough() -> None:
    pack = compile_seed(ROOT / "examples" / "seeds" / "acme-overrides.yaml", "acme-overrides")
    assert {r.id for r in pack.rules} == {"ACME-REL-001", "ACME-SEC-001", "ACME-COST-001"}
