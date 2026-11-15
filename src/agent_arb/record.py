"""Write the review record as Markdown for people and JSON for tools, plus the derived summaries."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import ComplianceRow, Finding, LevelSummary, Record, Rule

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def level_summary(area: str, rules: dict[str, Rule], findings: list[Finding], target: int) -> LevelSummary:
    """Observed level is the highest level at which every selected rule with that level passed."""
    by_level: dict[int, list[Finding]] = {}
    for f in findings:
        r = rules.get(f.rule_id)
        if r is not None and r.level is not None and area in r.tags:
            by_level.setdefault(r.level, []).append(f)
    observed = 0
    missing: list[str] = []
    for lvl in sorted(by_level):
        fails = [f for f in by_level[lvl] if f.verdict != "pass"]
        if fails or lvl != observed + 1:
            missing.extend(sorted({f.rule_id for f in fails}))
            break
        observed = lvl
    for lvl, fs in by_level.items():
        if lvl > observed:
            missing.extend(sorted({f.rule_id for f in fs if f.verdict != "pass"}))
    return LevelSummary(area=area, observed=observed, target=target, missing_rule_ids=sorted(set(missing)))


def compliance_rows(rules: dict[str, Rule], findings: list[Finding]) -> list[ComplianceRow]:
    rows: list[ComplianceRow] = []
    for f in findings:
        r = rules.get(f.rule_id)
        if r is None:
            continue
        for ref in r.compliance_refs:
            framework, _, reference = ref.partition(" ")
            rows.append(
                ComplianceRow(
                    framework=framework,
                    reference=reference or ref,
                    rule_id=r.id,
                    decision_id=f.decision_id,
                    verdict=f.verdict,
                    disposition=f.disposition,
                )
            )
    return sorted(rows, key=lambda r: (r.framework, r.reference))


SLO_PATTERN = re.compile(
    r"\b(p(?:50|90|95|99|99\.9)|percentile|availability|error budget|SLO|SLA|RPO|RTO)\b[^.\n]*", re.I
)


def service_levels(text: str) -> list[str]:
    seen: list[str] = []
    for m in SLO_PATTERN.finditer(text):
        s = re.sub(r"\s+", " ", m.group(0)).strip()
        if s not in seen and len(s) > 6:
            seen.append(s)
    return seen[:20]


def write_record(record: Record, rules: dict[str, Rule], out_dir: Path, stem: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{stem}.record.json"
    md_path = out_dir / f"{stem}.record.md"
    json_path.write_text(json.dumps(record.model_dump(mode="json"), indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(record, rules), encoding="utf-8")
    return md_path, json_path


def render_markdown(record: Record, rules: dict[str, Rule]) -> str:
    lines: list[str] = []
    lines.append(f"# Architecture review record: {record.document}")
    lines.append("")
    lines.append(
        f"Reviewed on {record.created_at[:10]} by {record.engine} {record.engine_version} "
        f"with model `{record.model}`. Service tier {record.tier}."
    )
    lines.append("")
    lines.append(
        "This is a design-time review of what the document states. It is not an assessment "
        "or attestation against any compliance framework."
    )
    lines.append("")
    if record.levels:
        lines.append("## Levels")
        lines.append("")
        for lv in record.levels:
            miss = f", missing {', '.join(lv.missing_rule_ids)}" if lv.missing_rule_ids else ""
            lines.append(f"- **{lv.area}**: observed level {lv.observed}, target level {lv.target}{miss}")
        lines.append("")
    if record.service_levels:
        lines.append("## Service levels stated in the document")
        lines.append("")
        lines.extend(f"- {s}" for s in record.service_levels)
        lines.append("")
    fails = [f for f in record.findings if f.verdict == "fail"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Decisions reviewed: {len(record.decisions)}")
    lines.append(f"- Findings: {len(record.findings)}, of which {len(fails)} failed")
    by_sev: dict[str, int] = {}
    for f in fails:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
    if by_sev:
        lines.append(
            "- Failed by severity: "
            + ", ".join(f"{k} {v}" for k, v in sorted(by_sev.items(), key=lambda kv: SEVERITY_ORDER[kv[0]]))
        )
    lines.append("")
    lines.append("## Decisions")
    lines.append("")
    for d in record.decisions:
        lines.append(f"### {d.id}. {d.title}")
        lines.append("")
        lines.append(
            f"Section {d.section_ref}. Scope {d.scope}. Tags: {', '.join(d.tags) or 'none'}."
            + (f" Data classes: {', '.join(d.data_classes)}." if d.data_classes else "")
        )
        lines.append("")
        if d.context:
            lines.append(f"**Context.** {d.context}")
            lines.append("")
        if d.options:
            lines.append("**Options considered.**")
            lines.append("")
            lines.extend(f"- {o.name}" + (f": {o.tradeoff}" if o.tradeoff else "") for o in d.options)
            lines.append("")
        if d.chosen:
            lines.append(f"**Chosen.** {d.chosen}")
            lines.append("")
        if d.implications:
            lines.append(f"**Implications.** {d.implications}")
            lines.append("")
        dfs = sorted(
            (f for f in record.findings if f.decision_id == d.id),
            key=lambda f: (f.verdict != "fail", SEVERITY_ORDER[f.severity], f.rule_id),
        )
        if dfs:
            lines.append("| Rule | Verdict | Severity | Disposition | Note |")
            lines.append("|---|---|---|---|---|")
            for f in dfs:
                title = rules[f.rule_id].title if f.rule_id in rules else f.rule_id
                note = f.explanation.replace("|", "/")
                if f.rationale:
                    note += f" Author: {f.rationale.replace('|', '/')}"
                lines.append(f"| {f.rule_id} {title} | {f.verdict} | {f.severity} | {f.disposition} | {note} |")
            lines.append("")
        advs = [a for a in record.advisories if a.decision_id == d.id]
        if advs:
            lines.append("**Advisory questions.**")
            lines.append("")
            for a in advs:
                lines.append(f"- {a.question}")
                lines.append(f"  Answer: {a.answer or '(not answered)'}")
            lines.append("")
    docfs = [f for f in record.findings if f.decision_id is None]
    if docfs:
        lines.append("## Document-level findings")
        lines.append("")
        lines.append("| Rule | Verdict | Severity | Disposition | Note |")
        lines.append("|---|---|---|---|---|")
        for f in sorted(docfs, key=lambda f: (f.verdict != "fail", SEVERITY_ORDER[f.severity], f.rule_id)):
            title = rules[f.rule_id].title if f.rule_id in rules else f.rule_id
            lines.append(
                f"| {f.rule_id} {title} | {f.verdict} | {f.severity} | {f.disposition} | {f.explanation.replace('|', '/')} |"
            )
        lines.append("")
    docadv = [a for a in record.advisories if a.decision_id is None]
    if docadv:
        lines.append("## Document-level advisory questions")
        lines.append("")
        for a in docadv:
            lines.append(f"- {a.question}")
            lines.append(f"  Answer: {a.answer or '(not answered)'}")
        lines.append("")
    if record.compliance:
        lines.append("## Compliance traceability")
        lines.append("")
        lines.append("Design-time traceability only. Not an assessment.")
        lines.append("")
        lines.append("| Framework | Reference | Rule | Decision | Verdict | Disposition |")
        lines.append("|---|---|---|---|---|---|")
        for c in record.compliance:
            lines.append(
                f"| {c.framework} | {c.reference} | {c.rule_id} | {c.decision_id or 'document'} | {c.verdict} | {c.disposition} |"
            )
        lines.append("")
    lines.append("## Rule packs used")
    lines.append("")
    for p in record.packs:
        lines.append(f"- {p.name} ({p.layer}) version {p.version}, hash {p.content_hash}, {p.rule_count} rules")
    lines.append("")
    return "\n".join(lines)
