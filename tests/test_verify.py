from agent_arb.models import Finding, Severity
from agent_arb.verify import quote_in, verify_findings

TEXT = "Calls to inventory have a 300 ms timeout and are retried twice.\nThe cluster runs in two zones."


def test_quote_matching_is_whitespace_and_case_insensitive() -> None:
    assert quote_in("calls to inventory have a   300 ms timeout", TEXT)
    assert not quote_in("timeout of 500 ms", TEXT)
    assert not quote_in("short", TEXT)


def test_ungrounded_pass_is_dropped_and_ungrounded_fail_is_kept_unverified() -> None:
    good = Finding(rule_id="A", decision_id="D1", verdict="fail", severity=Severity.HIGH, quote="runs in two zones")
    wrong = "runs in three zones"
    bad_pass = Finding(rule_id="B", decision_id="D1", verdict="pass", severity=Severity.HIGH, quote=wrong)
    bad_fail = Finding(rule_id="C", decision_id="D1", verdict="fail", severity=Severity.HIGH, quote=wrong)
    unclear = Finding(rule_id="D", decision_id="D1", verdict="unclear", severity=Severity.LOW)
    kept, dropped = verify_findings([good, bad_pass, bad_fail, unclear], TEXT)
    assert [f.rule_id for f in kept] == ["A", "C", "D"]
    assert [f.rule_id for f in dropped] == ["B"]
    assert good.verified and not bad_pass.verified and not bad_fail.verified
    assert bad_fail.quote == "" and "not in the text" in bad_fail.explanation


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


def test_not_applicable_is_kept_without_a_quote() -> None:
    na = Finding(rule_id="A", decision_id="D1", verdict="n/a", severity=Severity.HIGH, quote="runs in three zones")
    kept, dropped = verify_findings([na], TEXT)
    assert kept == [na] and not dropped and na.quote == "" and not na.verified


def test_short_quotes_must_be_verbatim() -> None:
    f = Finding(rule_id="A", decision_id="D1", verdict="pass", severity=Severity.HIGH, quote="runs in three zones")
    kept, dropped = verify_findings([f], TEXT)
    assert dropped and not kept


def test_failure_without_quote_is_kept_unverified_and_pass_without_quote_is_dropped() -> None:
    fail = Finding(rule_id="A", decision_id="D1", verdict="fail", severity=Severity.HIGH, explanation="nothing stated")
    ok = Finding(rule_id="B", decision_id="D1", verdict="pass", severity=Severity.HIGH)
    kept, dropped = verify_findings([fail, ok], TEXT)
    assert [f.rule_id for f in kept] == ["A"] and not kept[0].verified
    assert "no quote offered" in kept[0].explanation
    assert [f.rule_id for f in dropped] == ["B"]
