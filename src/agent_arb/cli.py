"""The agent-arb command line."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .compile import compile_seed, dump_pack
from .config import CONFIG_PATH, load_config, write_default_config
from .decisions import propose_decisions
from .ingest import outline, read_document, split_sections
from .llm import Model, ModelError, OpenAICompatibleModel
from .manifest import Manifest
from .models import AdvisoryAnswer, Decision, Finding, Layer, Pack, PackRef, Record, Rule, RuleType, Status
from .record import compliance_rows, level_summary, service_levels, write_record
from .review import advisories_for, judge_decision, judge_document
from .rules import RuleSet, load_builtin_packs, load_pack, load_packs_from_dir, load_tiers

app = typer.Typer(help="Agent ARB: an architecture review board you can run on your laptop.", no_args_is_help=True)
rules_app = typer.Typer(help="Compile, approve and inspect rule packs.", no_args_is_help=True)
app.add_typer(rules_app, name="rules")

LEVEL_AREAS = ("observability", "alerting", "resilience")


def _model_from_config() -> Model:
    cfg = load_config()
    return OpenAICompatibleModel(cfg.model.base_url, cfg.model.name, cfg.model.api_key, cfg.model.timeout_seconds)


def _load_all_packs(seeds: list[Path], project: Path | None, no_builtin: bool) -> list[Pack]:
    packs: list[Pack] = [] if no_builtin else load_builtin_packs()
    for s in seeds:
        if s.is_dir():
            packs.extend(load_packs_from_dir(s))
        elif s.suffix in {".yaml", ".yml"}:
            packs.append(load_pack(s))
        else:
            raise typer.BadParameter(f"{s} is not a compiled pack; run `agent-arb rules compile` first")
    if project is not None:
        p = load_pack(project)
        p.layer = Layer.PROJECT
        packs.append(p)
    return packs


@app.command()
def version() -> None:
    """Print the engine version."""
    typer.echo(f"agent-arb {__version__}")


@app.command()
def init() -> None:
    """Write the default config and check the model endpoint answers."""
    path = write_default_config()
    typer.echo(f"config: {path}")
    cfg = load_config()
    model = OpenAICompatibleModel(cfg.model.base_url, cfg.model.name, cfg.model.api_key, cfg.model.timeout_seconds)
    try:
        names = model.ping()
    except Exception as e:  # noqa: BLE001
        typer.secho(f"model endpoint {cfg.model.base_url} did not answer: {e}", fg="red")
        typer.echo("Start Ollama, or edit [model] in the config file to point at your endpoint.")
        raise typer.Exit(1) from None
    if cfg.model.name not in names:
        typer.secho(
            f"endpoint is up but model '{cfg.model.name}' is not loaded. Available: {', '.join(names) or 'none'}",
            fg="yellow",
        )
        typer.echo(f"Pull it (for Ollama: ollama pull {cfg.model.name}) or change [model].name in {CONFIG_PATH}.")
        raise typer.Exit(1)
    typer.secho(f"model '{cfg.model.name}' at {cfg.model.base_url} is ready", fg="green")


@app.command()
def ingest(document: Path) -> None:
    """Show how a document splits into sections. No model is used."""
    for s in split_sections(read_document(document)):
        typer.echo(f"{s.ref:>4}  L{s.start_line}-{s.end_line}  {'#' * s.level} {s.heading}  ({len(s.text)} chars)")


@app.command()
def review(
    document: Path,
    seeds: Annotated[
        list[Path], typer.Option("--seeds", "-s", help="Compiled company pack files or folders. Repeatable.")
    ] = None,
    project: Annotated[Path | None, typer.Option("--project", help="A project-level pack file.")] = None,
    out: Annotated[Path, typer.Option("--out", "-o", help="Output folder for the record and manifest.")] = Path(
        ".agent-arb"
    ),
    tier: Annotated[
        int | None, typer.Option("--tier", help="Service tier, 1 is most critical. Default from config.")
    ] = None,
    interactive: Annotated[
        bool, typer.Option("--interactive/--no-interactive", help="Confirm decisions and walk through findings.")
    ] = True,
    challenge: Annotated[
        bool | None, typer.Option("--challenge/--no-challenge", help="Ask advisory questions before showing findings.")
    ] = None,
    no_builtin: Annotated[bool, typer.Option("--no-builtin", help="Use only the packs you pass. For tests.")] = False,
    model_override: Annotated[str | None, typer.Option("--model", help="Model name, overriding config.")] = None,
) -> None:
    """Review a design document decision by decision and write a record."""
    if seeds is None:
        seeds = []
    cfg = load_config()
    tier = tier if tier is not None else cfg.review.default_tier
    challenge = cfg.review.challenge_mode if challenge is None else challenge
    model = _model_from_config()
    if model_override:
        model.name = model_override  # type: ignore[attr-defined]
    packs = _load_all_packs(seeds, project, no_builtin)
    run_review(document, packs, model, out, tier, interactive, challenge, cfg.review.rules_per_prompt)


def run_review(
    document: Path,
    packs: list[Pack],
    model: Model,
    out: Path,
    tier: int,
    interactive: bool,
    challenge: bool,
    rules_per_prompt: int = 6,
) -> Record:
    """The whole flow. Shared by the CLI and the evals."""
    ruleset = RuleSet(packs)
    text = read_document(document)
    sections = split_sections(text)
    by_ref = {s.ref: s for s in sections}
    out.mkdir(parents=True, exist_ok=True)
    manifest = Manifest(out / f"{document.stem}.manifest.jsonl")
    typer.echo(
        f"{len(sections)} sections, {len(ruleset.rules)} approved rules from {len(packs)} packs, model {model.name}"
    )
    for base, over, mode in ruleset.shadowed:
        typer.echo(f"  note: {over} {mode} {base}")

    # 1. decisions, one section per prompt
    decisions: list[Decision] = []
    for s in sections:
        try:
            found, dropped = propose_decisions(s, model, manifest, start_index=len(decisions) + 1)
        except ModelError as e:
            typer.secho(f"  {s.ref} {s.heading}: model error, skipped ({e})", fg="yellow")
            continue
        decisions.extend(found)
        note = f", {dropped} dropped for an evidence quote not in the text" if dropped else ""
        typer.echo(f"  {s.ref} {s.heading}: {len(found)} decision(s){note}")
    if interactive:
        decisions = _confirm_decisions(decisions)
    else:
        for d in decisions:
            d.confirmed = True

    # 2. per decision: select, advisories, judge, verify, walk-through
    findings: list[Finding] = []
    advisories: list[AdvisoryAnswer] = []
    for d in decisions:
        section = by_ref[d.section_ref]
        selected = ruleset.select(d, tier)
        advs = advisories_for(d, selected)
        if interactive and challenge:
            _ask_advisories(d, advs)
        try:
            kept, dropped = judge_decision(d, section, selected, model, manifest, rules_per_prompt)
        except ModelError as e:
            typer.secho(f"  {d.id}: model error, no findings ({e})", fg="yellow")
            kept, dropped = [], []
        if dropped:
            typer.echo(f"  {d.id}: dropped {len(dropped)} finding(s) whose quote was not in the text")
        if interactive:
            _walk_through(d, kept, ruleset.rules)
            if not challenge:
                _ask_advisories(d, advs)
        findings.extend(kept)
        advisories.extend(advs)
        typer.echo(f"  {d.id} {d.title}: {len(selected)} rules, {sum(1 for f in kept if f.verdict == 'fail')} failed")

    # 3. document-target rules against the outline
    doc_rules = ruleset.document_rules(tier)
    doc_advs = advisories_for(None, doc_rules)
    try:
        doc_kept, _ = judge_document(outline(sections), doc_rules, model, manifest)
    except ModelError as e:
        typer.secho(f"  document: model error ({e})", fg="yellow")
        doc_kept = []
    if interactive:
        _walk_through(None, doc_kept, ruleset.rules)
        _ask_advisories(None, doc_advs)
    findings.extend(doc_kept)
    advisories.extend(doc_advs)

    # 4. summaries and record
    tiers = load_tiers()
    targets = tiers.get("targets", {}) if isinstance(tiers, dict) else {}
    target = int(targets.get(str(tier), targets.get("default", 2)))
    levels = [level_summary(area, ruleset.rules, findings, target) for area in LEVEL_AREAS]
    record = Record(
        engine="agent-arb",
        engine_version=__version__,
        model=model.name,
        document=document.name,
        tier=tier,
        packs=[
            PackRef(name=p.name, layer=p.layer, version=p.version, content_hash=p.content_hash, rule_count=len(p.rules))
            for p in packs
        ],
        decisions=decisions,
        findings=findings,
        advisories=advisories,
        levels=[lv for lv in levels if lv.observed or lv.missing_rule_ids],
        compliance=compliance_rows(ruleset.rules, findings),
        service_levels=service_levels(text),
    )
    md, js = write_record(record, ruleset.rules, out, document.stem)
    typer.secho(f"record: {md}\n        {js}\nmanifest: {manifest.path}", fg="green")
    return record


def _confirm_decisions(decisions: list[Decision]) -> list[Decision]:
    typer.echo("\nProposed decisions. For each: [k]eep, [e]dit title, [d]rop.")
    kept: list[Decision] = []
    for d in decisions:
        typer.echo(
            f"\n{d.id}. {d.title}\n   section {d.section_ref}, scope {d.scope}, tags {', '.join(d.tags) or 'none'}"
        )
        if d.evidence_quote:
            typer.echo(f'   "{d.evidence_quote[:160]}"')
        choice = typer.prompt("   keep/edit/drop", default="k").strip().lower()[:1]
        if choice == "d":
            continue
        if choice == "e":
            d.title = typer.prompt("   title", default=d.title)
            tags = typer.prompt("   tags (comma separated)", default=", ".join(d.tags))
            d.tags = [t.strip() for t in tags.split(",") if t.strip()]
        d.confirmed = True
        kept.append(d)
    for i, d in enumerate(kept, start=1):
        d.id = f"D{i}"
    return kept


def _walk_through(decision: Decision | None, findings: list[Finding], rules: dict[str, Rule]) -> None:
    fails = [f for f in findings if f.verdict != "pass"]
    if not fails:
        return
    head = f"{decision.id} {decision.title}" if decision else "Document-level"
    typer.echo(f"\n{head}: {len(fails)} finding(s) to walk through. [a]ccept, [d]ispute, [r]evise, [w]aive, [s]kip")
    for f in fails:
        title = rules[f.rule_id].title if f.rule_id in rules else f.rule_id
        typer.echo(f"\n  {f.rule_id} [{f.severity}] {title}: {f.verdict}")
        typer.echo(f"  {f.explanation}")
        if f.quote:
            typer.echo(f'  quote: "{f.quote[:200]}"')
        choice = typer.prompt("  disposition", default="a").strip().lower()[:1]
        mapping = {"a": "accepted", "d": "disputed", "r": "revised", "w": "waived", "s": "open"}
        f.disposition = mapping.get(choice, "open")  # type: ignore[assignment]
        if f.disposition in {"disputed", "revised", "waived"}:
            f.rationale = typer.prompt("  rationale", default="")


def _ask_advisories(decision: Decision | None, advisories: list[AdvisoryAnswer]) -> None:
    if not advisories:
        return
    head = f"{decision.id} {decision.title}" if decision else "Document-level"
    typer.echo(f"\n{head}: {len(advisories)} question(s) from the board.")
    for a in advisories:
        a.answer = typer.prompt(f"  {a.question}\n  answer", default="").strip()


@rules_app.command("compile")
def rules_compile(
    seed: Path,
    out: Annotated[Path, typer.Option("--out", "-o")] = Path("company-pack.yaml"),
    name: Annotated[str | None, typer.Option("--name")] = None,
) -> None:
    """Compile a seed document (PDF, Markdown or YAML) into a draft pack. No model is used."""
    pack = compile_seed(seed, name or seed.stem)
    dump_pack(pack, out)
    drafts = sum(1 for r in pack.rules if r.status == Status.DRAFT)
    typer.echo(f"{len(pack.rules)} rules ({drafts} draft) written to {out}. Run `agent-arb rules approve {out}`.")


@rules_app.command("approve")
def rules_approve(pack_path: Path, reviewer: Annotated[str, typer.Option("--reviewer")] = "") -> None:
    """Walk through draft rules and approve, edit, reject or skip each."""
    from datetime import date

    pack = load_pack(pack_path)
    reviewer = reviewer or typer.prompt("reviewer name")
    for r in pack.rules:
        if r.status != Status.DRAFT:
            continue
        typer.echo(
            f"\n{r.id} [{r.severity}] {r.title}\n  {r.requirement}\n  tags: {', '.join(r.tags)}  source: {r.source.name} {r.source.locator}"  # noqa: E501
        )
        choice = typer.prompt("  [a]pprove, [e]dit, [r]eject, [s]kip", default="a").strip().lower()[:1]
        if choice == "s":
            continue
        if choice == "r":
            r.status = Status.REJECTED
        else:
            if choice == "e":
                r.title = typer.prompt("  title", default=r.title)
                r.requirement = typer.prompt("  requirement", default=r.requirement)
                r.severity = typer.prompt("  severity", default=r.severity)  # type: ignore[assignment]
                tags = typer.prompt("  tags", default=", ".join(r.tags))
                r.tags = [t.strip() for t in tags.split(",") if t.strip()]
            r.status = Status.APPROVED
        r.reviewed_by = reviewer
        r.reviewed_on = date.today().isoformat()
    pack.version = pack.version.replace("-draft", "")
    dump_pack(pack, pack_path)
    approved = sum(1 for r in pack.rules if r.status == Status.APPROVED)
    typer.echo(
        f"{approved} approved, {sum(1 for r in pack.rules if r.status == Status.DRAFT)} still draft, written to {pack_path}"  # noqa: E501
    )


@rules_app.command("list")
def rules_list(
    seeds: Annotated[list[Path], typer.Option("--seeds", "-s")] = None,
    no_builtin: Annotated[bool, typer.Option("--no-builtin")] = False,
) -> None:
    """List approved rules after precedence, and report overridden base rules."""
    if seeds is None:
        seeds = []
    rs = RuleSet(_load_all_packs(seeds, None, no_builtin))
    for r in rs.rules.values():
        typer.echo(f"{r.id:<16} {r.severity:<8} {r.scope:<14} {r.target:<9} {r.type:<8} {r.title}")
    typer.echo(f"\n{len(rs.rules)} rules")
    for base, over, mode in rs.shadowed:
        typer.echo(f"  {over} {mode} {base}")


@rules_app.command("coverage")
def rules_coverage(seeds: Annotated[list[Path], typer.Option("--seeds", "-s")] = None) -> None:
    """Rules per tag and scope. Thin cells are the gap list."""
    if seeds is None:
        seeds = []
    rs = RuleSet(_load_all_packs(seeds, None, False))
    grid = rs.coverage()
    scopes = ["architecture", "design", "implementation", "practice"]
    typer.echo(f"{'tag':<18}" + "".join(f"{s:>16}" for s in scopes))
    for tag in sorted(grid):
        typer.echo(f"{tag:<18}" + "".join(f"{grid[tag].get(s, 0):>16}" for s in scopes))


@rules_app.command("select")
def rules_select(
    decision_json: Path, tier: int = 2, seeds: Annotated[list[Path], typer.Option("--seeds", "-s")] = None
) -> None:
    """Show which rules a decision (as JSON) would pull in. For debugging packs."""
    if seeds is None:
        seeds = []
    d = Decision.model_validate(json.loads(decision_json.read_text(encoding="utf-8")))
    rs = RuleSet(_load_all_packs(seeds, None, False))
    for r in rs.select(d, tier):
        typer.echo(f"{r.id:<16} {r.type:<8} {r.title}")


@rules_app.command("validate")
def rules_validate(path: Path) -> None:
    """Validate a pack file or folder against the schema."""
    paths = sorted(path.rglob("*.yaml")) if path.is_dir() else [path]
    bad = 0
    for p in paths:
        if p.name in {"canon.yaml", "tiers.yaml"}:
            continue
        try:
            pack = load_pack(p)
            ids = [r.id for r in pack.rules]
            dupes = {i for i in ids if ids.count(i) > 1}
            if dupes:
                raise ValueError(f"duplicate ids {sorted(dupes)}")
            for r in pack.rules:
                if r.type == RuleType.CHECK and not r.requirement:
                    raise ValueError(f"{r.id}: check rule without requirement")
                if r.type == RuleType.ADVISORY and not r.question:
                    raise ValueError(f"{r.id}: advisory rule without question")
            typer.echo(f"ok   {p} ({len(pack.rules)} rules)")
        except Exception as e:  # noqa: BLE001
            bad += 1
            typer.secho(f"FAIL {p}: {e}", fg="red")
    if bad:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
