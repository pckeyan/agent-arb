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


def test_paraphrased_quote_is_repaired_to_the_real_sentence() -> None:
    f = Finding(
        rule_id="A",
        decision_id="D1",
        verdict="pass",
        severity=Severity.HIGH,
        quote="inventory calls have a 300 ms timeout and get retried twice",
    )
    kept, dropped = verify_findings([f], TEXT)
    assert kept and not dropped
    assert kept[0].quote == "Calls to inventory have a 300 ms timeout and are retried twice."
    assert "nearest sentence" in kept[0].explanation


def test_unrelated_quote_is_not_repaired() -> None:
    f = Finding(
        rule_id="A",
        decision_id="D1",
        verdict="pass",
        severity=Severity.HIGH,
        quote="the payment gateway tokenises the card number at the edge",
    )
    kept, dropped = verify_findings([f], TEXT)
    assert dropped and not kept


def test_contradicting_number_blocks_repair() -> None:
    f = Finding(
        rule_id="A",
        decision_id="D1",
        verdict="pass",
        severity=Severity.HIGH,
        quote="calls to inventory have a 500 ms timeout and are retried",
    )
    kept, dropped = verify_findings([f], TEXT)
    assert dropped and not kept


def test_short_quotes_must_be_verbatim() -> None:
    f = Finding(rule_id="A", decision_id="D1", verdict="fail", severity=Severity.HIGH, quote="runs in three zones")
    kept, dropped = verify_findings([f], TEXT)
    assert dropped and not kept
