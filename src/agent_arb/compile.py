"""Turn seed documents into a draft rule pack, locally.

YAML seeds are taken as rules. Markdown seeds become one rule per heading or
bullet that reads like a requirement. PDF seeds are extracted page by page
with pypdf and then treated like Markdown. Every produced rule is a draft
until a person approves it.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .ingest import _pdf_to_text
from .models import Layer, Pack, Rule, Source, Status

REQUIREMENT_WORDS = re.compile(r"\b(must|shall|should|required|never|always|at least|no (?:more|less) than)\b", re.I)
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
PAGE = re.compile(r"<!-- page (\d+) -->")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def _guess_tags(text: str) -> list[str]:
    tags = []
    for tag, words in {
        "security": ("auth", "encrypt", "tls", "secret", "token", "identity", "pci", "cardholder"),
        "observability": ("metric", "log", "trace", "alert", "slo", "p99", "p95", "dashboard"),
        "resilience": ("timeout", "retry", "circuit", "bulkhead", "failover", "degrad"),
        "recovery": ("backup", "restore", "rpo", "rto", "disaster"),
        "data": ("database", "storage", "retention", "schema", "replication"),
        "scalability": ("scale", "capacity", "throughput", "load"),
        "delivery": ("deploy", "pipeline", "release", "rollback"),
        "api": ("api", "contract", "version"),
    }.items():
        if any(w in text.lower() for w in words):
            tags.append(tag)
    return tags or ["general"]


def compile_seed(path: Path, pack_name: str, layer: Layer = Layer.COMPANY) -> Pack:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict) and "rules" in raw:
            pack = Pack.model_validate(
                {"name": pack_name, "layer": layer, **{k: v for k, v in raw.items() if k != "layer"}}
            )
            pack.layer = layer
            return pack
        rules = raw if isinstance(raw, list) else []
        return Pack(name=pack_name, layer=layer, rules=[Rule.model_validate(r) for r in rules])
    if suffix == ".pdf":
        text = _pdf_to_text(path)
    elif suffix in {".md", ".markdown", ".txt"}:
        text = path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"unsupported seed type: {path.suffix}")
    return _compile_text(text, path, pack_name, layer)


def _compile_text(text: str, path: Path, pack_name: str, layer: Layer) -> Pack:
    rules: list[Rule] = []
    heading = "General"
    page = ""
    prefix = _slug(pack_name).upper().replace("-", "")[:6] or "SEED"
    n = 0
    for line in text.splitlines():
        pm = PAGE.search(line)
        if pm:
            page = f"page {pm.group(1)}"
            continue
        hm = HEADING.match(line)
        if hm:
            heading = hm.group(2)
            continue
        bm = BULLET.match(line)
        candidate = bm.group(1) if bm else line.strip()
        if not candidate or not REQUIREMENT_WORDS.search(candidate) or len(candidate) < 25:
            continue
        n += 1
        locator = f"{heading}" + (f", {page}" if page else "")
        rules.append(
            Rule(
                id=f"{prefix}-{n:03d}",
                title=candidate[:80].rstrip(" ,.;:"),
                requirement=candidate,
                tags=_guess_tags(f"{heading} {candidate}"),
                evidence_hints=[w for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", candidate)[:6]],
                source=Source(kind="company", name=path.name, locator=locator, text_reused="adapted"),
                status=Status.DRAFT,
            )
        )
    return Pack(
        name=pack_name,
        layer=layer,
        version="0.1.0-draft",
        description=f"Compiled from {path.name}; every rule is a draft until approved.",
        rules=rules,
    )


def dump_pack(pack: Pack, path: Path) -> None:
    data = pack.model_dump(mode="json", exclude={"content_hash"})
    for r in data["rules"]:
        for k in (
            "applies_when",
            "overrides",
            "reviewed_by",
            "reviewed_on",
            "compliance_refs",
            "expects",
            "level",
            "question",
        ):
            v = r.get(k)
            if v in (None, "", [], {}) or v == {"data_classes": [], "tags_any": [], "min_tier": None}:
                r.pop(k, None)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8")
