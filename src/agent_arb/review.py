"""Judge one decision against its selected rules, then verify the quotes.

This module has no interactive code; the CLI and the evals drive it.
"""

from __future__ import annotations

from importlib import resources

from .llm import Model
from .manifest import Manifest
from .models import AdvisoryAnswer, Decision, Finding, ManifestEntry, Rule, RuleType, Section
from .verify import verify_findings


def _prompt(name: str) -> str:
    return (resources.files("agent_arb") / "prompts" / name).read_text(encoding="utf-8")


def packet_text(decision: Decision, section: Section) -> str:
    """What the model sees about a decision: the decision fields and its section text."""
    opts = "\n".join(f"  - {o.name}: {o.tradeoff}" for o in decision.options) or "  (none stated)"
    return (
        f"DECISION {decision.id}: {decision.title}\n"
        f"Scope: {decision.scope}\nTags: {', '.join(decision.tags)}\n"
        f"Data classes: {', '.join(decision.data_classes) or 'none stated'}\n"
        f"Context: {decision.context}\nOptions:\n{opts}\nChosen: {decision.chosen}\n"
        f"Implications: {decision.implications}\n\n"
        f"SECTION TEXT ({section.ref}: {section.heading}):\n{section.text}"
    )


def rules_text(rules: list[Rule]) -> str:
    rows = []
    for r in rules:
        exp = f" Expects: {', '.join(r.expects)}." if r.expects else ""
        rows.append(f"- {r.id} [{r.severity}] {r.title}: {r.requirement}{exp}")
    return "\n".join(rows)


def judge_decision(
    decision: Decision,
    section: Section,
    rules: list[Rule],
    model: Model,
    manifest: Manifest,
    rules_per_prompt: int = 6,
) -> tuple[list[Finding], list[Finding]]:
    """Judge in batches of a few rules so small models answer every rule. One section per prompt, always."""
    checks = [r for r in rules if r.type == RuleType.CHECK]
    if not checks:
        return [], []
    findings: list[Finding] = []
    for start in range(0, len(checks), max(1, rules_per_prompt)):
        findings.extend(
            _judge_batch(decision, section, checks[start : start + max(1, rules_per_prompt)], model, manifest)
        )
    return verify_findings(findings, packet_text(decision, section))


def _judge_batch(
    decision: Decision, section: Section, checks: list[Rule], model: Model, manifest: Manifest
) -> list[Finding]:
    system = _prompt("review.md")
    user = f"{packet_text(decision, section)}\n\nRULES:\n{rules_text(checks)}"
    manifest.add(
        ManifestEntry(
            step="judge",
            decision_id=decision.id,
            sections=[section.ref],
            rule_ids=[r.id for r in checks],
            prompt_chars=len(system) + len(user),
            model=model.name,
        )
    )
    reply = model.complete_json(system, user)
    by_id = {r.id: r for r in checks}
    findings: list[Finding] = []
    for raw in reply.get("findings", []) or []:
        if not isinstance(raw, dict) or raw.get("rule_id") not in by_id:
            continue
        verdict = str(raw.get("verdict", "unclear")).lower()
        if verdict not in {"pass", "fail", "unclear"}:
            verdict = "unclear"
        rule = by_id[raw["rule_id"]]
        findings.append(
            Finding(
                rule_id=rule.id,
                decision_id=decision.id,
                verdict=verdict,  # type: ignore[arg-type]
                severity=rule.severity,
                quote=str(raw.get("quote", "")),
                explanation=str(raw.get("explanation", "")),
            )
        )
    # A rule the model skipped is reported as unclear so nothing disappears silently.
    seen = {f.rule_id for f in findings}
    for r in checks:
        if r.id not in seen:
            findings.append(
                Finding(
                    rule_id=r.id,
                    decision_id=decision.id,
                    verdict="unclear",
                    severity=r.severity,
                    explanation="The model returned no finding for this rule.",
                )
            )
    return findings


def judge_document(
    outline: str, rules: list[Rule], model: Model, manifest: Manifest
) -> tuple[list[Finding], list[Finding]]:
    checks = [r for r in rules if r.type == RuleType.CHECK]
    if not checks:
        return [], []
    system = _prompt("document.md")
    user = f"DOCUMENT OUTLINE:\n{outline}\n\nRULES:\n{rules_text(checks)}"
    manifest.add(
        ManifestEntry(
            step="judge-document",
            rule_ids=[r.id for r in checks],
            prompt_chars=len(system) + len(user),
            model=model.name,
        )
    )
    reply = model.complete_json(system, user)
    by_id = {r.id: r for r in checks}
    findings: list[Finding] = []
    for raw in reply.get("findings", []) or []:
        if not isinstance(raw, dict) or raw.get("rule_id") not in by_id:
            continue
        verdict = str(raw.get("verdict", "unclear")).lower()
        if verdict not in {"pass", "fail", "unclear"}:
            verdict = "unclear"
        rule = by_id[raw["rule_id"]]
        findings.append(
            Finding(
                rule_id=rule.id,
                decision_id=None,
                verdict=verdict,  # type: ignore[arg-type]
                severity=rule.severity,
                quote=str(raw.get("quote", "")),
                explanation=str(raw.get("explanation", "")),
            )
        )
    seen = {f.rule_id for f in findings}
    for r in checks:
        if r.id not in seen:
            findings.append(
                Finding(
                    rule_id=r.id,
                    decision_id=None,
                    verdict="unclear",
                    severity=r.severity,
                    explanation="The model returned no finding for this rule.",
                )
            )
    return verify_findings(findings, outline)


def advisories_for(decision: Decision | None, rules: list[Rule]) -> list[AdvisoryAnswer]:
    return [
        AdvisoryAnswer(rule_id=r.id, decision_id=decision.id if decision else None, question=r.question)
        for r in rules
        if r.type == RuleType.ADVISORY
    ]
