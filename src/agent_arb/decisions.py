"""Propose decisions from one section at a time. The model sees one section per prompt."""

from __future__ import annotations

from importlib import resources

from .llm import Model
from .manifest import Manifest
from .models import DATA_CLASSES, Decision, ManifestEntry, Option, Scope, Section
from .verify import quote_in

TAG_VOCABULARY = [
    "reliability",
    "availability",
    "resilience",
    "failure",
    "timeout",
    "retry",
    "backpressure",
    "spof",
    "recovery",
    "backup",
    "data",
    "durability",
    "replication",
    "consistency",
    "scalability",
    "capacity",
    "performance",
    "latency",
    "observability",
    "metrics",
    "logging",
    "tracing",
    "alerting",
    "slo",
    "security",
    "auth",
    "authz",
    "identity",
    "tls",
    "secrets",
    "pci",
    "cardholder-data",
    "encryption",
    "key-management",
    "cost",
    "messaging",
    "integration",
    "idempotency",
    "ordering",
    "api",
    "versioning",
    "concurrency",
    "threads",
    "domain",
    "boundaries",
    "coupling",
    "delivery",
    "deployment",
    "testing",
    "caching",
    "storage",
    "network",
    "multi-region",
    "tenancy",
]


def _prompt() -> str:
    text = (resources.files("agent_arb") / "prompts" / "decisions.md").read_text(encoding="utf-8")
    return text.replace("{tags}", ", ".join(TAG_VOCABULARY)).replace("{data_classes}", ", ".join(DATA_CLASSES))


def propose_decisions(
    section: Section, model: Model, manifest: Manifest, start_index: int
) -> tuple[list[Decision], int]:
    """Returns the decisions kept and how many were dropped for an evidence quote not found in the section."""
    system = _prompt()
    user = f"SECTION {section.ref}: {section.heading}\n\n{section.text}"
    manifest.add(
        ManifestEntry(step="decisions", sections=[section.ref], prompt_chars=len(system) + len(user), model=model.name)
    )
    reply = model.complete_json(system, user)
    out: list[Decision] = []
    dropped = 0
    for raw in reply.get("decisions", []) or []:
        if not isinstance(raw, dict) or not raw.get("title"):
            continue
        if not quote_in(str(raw.get("evidence_quote", "")), section.text):
            dropped += 1
            continue
        i = len(out)
        scope_raw = str(raw.get("scope", "architecture")).lower()
        scope = (
            Scope(scope_raw)
            if scope_raw in {s.value for s in Scope} and scope_raw != "practice"
            else Scope.ARCHITECTURE
        )
        tags = [t for t in (raw.get("tags") or []) if t in TAG_VOCABULARY]
        data_classes = [d for d in (raw.get("data_classes") or []) if d in DATA_CLASSES]
        options = [
            Option(name=str(o.get("name", "")), tradeoff=str(o.get("tradeoff", "")))
            for o in (raw.get("options") or [])
            if isinstance(o, dict) and o.get("name")
        ]
        out.append(
            Decision(
                id=f"D{start_index + i}",
                title=str(raw["title"]).strip(),
                section_ref=section.ref,
                scope=scope,
                context=str(raw.get("context", "")),
                options=options,
                chosen=str(raw.get("chosen", "")),
                implications=str(raw.get("implications", "")),
                evidence_quote=str(raw.get("evidence_quote", "")),
                tags=tags,
                data_classes=data_classes,
            )
        )
    return out, dropped
