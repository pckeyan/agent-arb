from agent_arb.models import Finding, Severity
from agent_arb.verify import quote_in, verify_findings

TEXT = "Calls to inventory have a 300 ms timeout and are retried twice.\nThe cluster runs in two zones."


def test_quote_matching_is_whitespace_and_case_insensitive() -> None:
    assert quote_in("calls to inventory have a   300 ms timeout", TEXT)
    assert not quote_in("timeout of 500 ms", TEXT)
    assert not quote_in("short", TEXT)


def test_unverifiable_findings_are_dropped() -> None:
    good = Finding(rule_id="A", decision_id="D1", verdict="fail", severity=Severity.HIGH, quote="runs in two zones")
    bad = Finding(rule_id="B", decision_id="D1", verdict="fail", severity=Severity.HIGH, quote="runs in three zones")
    unclear = Finding(rule_id="C", decision_id="D1", verdict="unclear", severity=Severity.LOW)
    kept, dropped = verify_findings([good, bad, unclear], TEXT)
    assert [f.rule_id for f in kept] == ["A", "C"]
    assert [f.rule_id for f in dropped] == ["B"]
    assert good.verified and not bad.verified
