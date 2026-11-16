from pathlib import Path

from agent_arb.models import Decision, Layer, Pack, Rule, Scope, Source, Status
from agent_arb.rules import RuleSet, expand_tags, load_builtin_packs, load_pack

ROOT = Path(__file__).resolve().parents[1]


def _rule(id: str, tags: list[str], **kw) -> Rule:
    return Rule(id=id, title=id, tags=tags, requirement="r", source=Source(kind="company", name="t"), **kw)


def test_builtin_packs_load_and_validate() -> None:
    packs = load_builtin_packs()
    rs = RuleSet(packs)
    assert len(rs.rules) > 80
    ids = [r.id for p in packs for r in p.rules]
    assert len(ids) == len(set(ids)), "duplicate rule ids"
    for p in packs:
        for r in p.rules:
            assert r.source.name, f"{r.id} has no source"
            if r.type == "check":
                assert r.requirement, f"{r.id} check without requirement"
            else:
                assert r.question, f"{r.id} advisory without question"
            if r.source.kind == "author-principle":
                assert r.source.text_reused == "none", f"{r.id} author rule claims reused text"


def test_precedence_supersedes_tightens_waives() -> None:
    base = Pack(name="b", layer=Layer.BASE, rules=[_rule("B-1", ["x"]), _rule("B-2", ["x"]), _rule("B-3", ["x"])])
    company = Pack(
        name="c",
        layer=Layer.COMPANY,
        rules=[
            _rule("C-1", ["x"], overrides={"mode": "supersedes", "rule": "B-1"}),
            _rule("C-2", ["x"], overrides={"mode": "tightens", "rule": "B-2"}),
            _rule("C-3", ["x"], overrides={"mode": "waives", "rule": "B-3", "reason": "n/a"}),
        ],
    )
    rs = RuleSet([company, base])
    assert set(rs.rules) == {"C-1", "B-2", "C-2"}
    assert ("B-1", "C-1", "supersedes") in rs.shadowed
    assert ("B-3", "C-3", "waives") in rs.shadowed


def test_draft_rules_never_run() -> None:
    p = Pack(name="d", layer=Layer.COMPANY, rules=[_rule("D-1", ["x"], status=Status.DRAFT)])
    assert RuleSet([p]).rules == {}


def test_select_by_scope_tags_and_data_class() -> None:
    rs = RuleSet(load_builtin_packs())
    d = Decision(
        id="D1",
        title="t",
        section_ref="S1",
        scope=Scope.ARCHITECTURE,
        tags=["auth", "tls"],
        data_classes=["cardholder-data"],
    )
    ids = {r.id for r in rs.select(d, tier=1)}
    assert "IND-SEC-S2S-001" in ids
    assert "IND-SEC-PCI-003" in ids
    assert "PRC-DEC-001" in ids  # practice rules apply to every decision
    assert "AUT-CONC-001" not in ids  # implementation scope
    d2 = Decision(id="D2", title="t", section_ref="S1", tags=["cost"])
    ids2 = {r.id for r in rs.select(d2, tier=3)}
    assert "IND-SEC-PCI-003" not in ids2
    assert "IND-COST-001" in ids2


def test_tag_families_widen_selection() -> None:
    assert {"metrics", "observability"} <= expand_tags(["metrics"])
    assert {"backup", "recovery", "data"} <= expand_tags(["backup"])
    assert "security" not in expand_tags(["metrics"])
    pack = Pack(name="t", layer=Layer.BASE, rules=[_rule("OBS", ["observability", "latency"])])
    d = Decision(id="D1", title="t", section_ref="S1", scope=Scope.ARCHITECTURE, tags=["alerting"])
    assert [r.id for r in RuleSet([pack]).select(d, tier=2)] == ["OBS"]


def test_tier_gating() -> None:
    rs = RuleSet(load_builtin_packs())
    d = Decision(id="D1", title="t", section_ref="S1", tags=["alerting", "observability"])
    assert "IND-OBS-012" in {r.id for r in rs.select(d, tier=1)}
    assert "IND-OBS-012" not in {r.id for r in rs.select(d, tier=2)}


def test_example_company_pack_overrides_base() -> None:
    rs = RuleSet(load_builtin_packs() + [load_pack(ROOT / "examples" / "seeds" / "acme-overrides.yaml")])
    assert "IND-SEC-S2S-002" not in rs.rules
    assert "ACME-SEC-001" in rs.rules
    assert "IND-COST-002" not in rs.rules
    assert "IND-REL-003" in rs.rules and "ACME-REL-001" in rs.rules
