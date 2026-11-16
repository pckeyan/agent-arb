"""Load rule packs, apply precedence, and select rules for a decision. No model here."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from importlib import resources
from pathlib import Path

import yaml

from .models import Decision, Layer, Pack, Rule, Status, Target

LAYER_ORDER = {Layer.BASE: 0, Layer.COMPANY: 1, Layer.PROJECT: 2}

# A decision tagged with a specific concern also matches rules tagged with its family.
# A "metrics" decision is an observability decision; a "backup" decision is a recovery and a data decision.
TAG_FAMILIES: dict[str, list[str]] = {
    "observability": ["metrics", "logging", "tracing", "alerting", "slo"],
    "resilience": ["timeout", "retry", "backpressure", "failure", "spof"],
    "reliability": ["availability", "spof", "multi-region"],
    "security": [
        "auth",
        "authz",
        "identity",
        "tls",
        "secrets",
        "pci",
        "cardholder-data",
        "encryption",
        "key-management",
    ],
    "recovery": ["backup", "durability", "replication"],
    "data": ["storage", "backup", "replication", "durability", "consistency", "caching"],
    "integration": ["messaging", "api"],
}


def expand_tags(tags: Iterable[str]) -> set[str]:
    """The decision's tags plus every family they belong to."""
    out = set(tags)
    for family, members in TAG_FAMILIES.items():
        if out & set(members):
            out.add(family)
    return out


def load_pack(path: Path) -> Pack:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    pack = Pack.model_validate(raw)
    pack.content_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return pack


def load_packs_from_dir(root: Path) -> list[Pack]:
    return [load_pack(p) for p in sorted(root.rglob("*.yaml")) if p.name not in {"canon.yaml", "tiers.yaml"}]


def builtin_packs_dir() -> Path:
    """The packs shipped inside the wheel, or the repo's rules/ when run from source."""
    try:
        packaged = resources.files("agent_arb") / "packs"
        if packaged.is_dir():
            return Path(str(packaged))
    except (ModuleNotFoundError, TypeError):
        pass
    repo_rules = Path(__file__).resolve().parents[2] / "rules"
    if repo_rules.is_dir():
        return repo_rules
    raise FileNotFoundError("built-in rule packs not found")


def load_builtin_packs() -> list[Pack]:
    return load_packs_from_dir(builtin_packs_dir())


class RuleSet:
    """All approved rules after precedence is applied, plus a shadow report."""

    def __init__(self, packs: Iterable[Pack]):
        self.packs = sorted(packs, key=lambda p: LAYER_ORDER[p.layer])
        self.rules: dict[str, Rule] = {}
        self.shadowed: list[tuple[str, str, str]] = []  # (base rule, overriding rule, mode)
        self._apply()

    def _apply(self) -> None:
        for pack in self.packs:
            for rule in pack.rules:
                if rule.status != Status.APPROVED:
                    continue
                if rule.overrides is not None:
                    target = rule.overrides.rule
                    mode = rule.overrides.mode
                    if target in self.rules:
                        self.shadowed.append((target, rule.id, mode))
                        if mode in {"supersedes", "waives"}:
                            del self.rules[target]
                    if mode == "waives":
                        continue
                self.rules[rule.id] = rule

    def select(self, decision: Decision, tier: int) -> list[Rule]:
        """Rules whose scope, tags and conditions match one decision."""
        out: list[Rule] = []
        dtags = expand_tags(decision.tags)
        for rule in self.rules.values():
            if rule.target != Target.DECISION:
                continue
            if rule.scope != "practice" and rule.scope != decision.scope:
                continue
            class_match = bool(set(rule.applies_when.data_classes) & set(decision.data_classes))
            if rule.tags and rule.scope != "practice" and not class_match and not (dtags & set(rule.tags)):
                continue
            if not self._applies(rule, dtags, decision, tier):
                continue
            out.append(rule)
        return sorted(out, key=lambda r: r.id)

    def document_rules(self, tier: int) -> list[Rule]:
        return sorted(
            (r for r in self.rules.values() if r.target == Target.DOCUMENT and self._tier_ok(r, tier)),
            key=lambda r: r.id,
        )

    @staticmethod
    def _tier_ok(rule: Rule, tier: int) -> bool:
        return rule.applies_when.min_tier is None or tier <= rule.applies_when.min_tier

    def _applies(self, rule: Rule, dtags: set[str], decision: Decision, tier: int) -> bool:
        cond = rule.applies_when
        if cond.data_classes and not (set(cond.data_classes) & set(decision.data_classes)):
            return False
        if cond.tags_any and not (set(cond.tags_any) & dtags):
            return False
        return self._tier_ok(rule, tier)

    def coverage(self) -> dict[str, dict[str, int]]:
        """Rules per (first tag, scope). The thin cells are the gap list."""
        grid: dict[str, dict[str, int]] = {}
        for rule in self.rules.values():
            key = rule.tags[0] if rule.tags else "untagged"
            grid.setdefault(key, {}).setdefault(rule.scope, 0)
            grid[key][rule.scope] += 1
        return grid


def load_tiers(path: Path | None = None) -> dict[str, dict[str, int]]:
    p = path or (builtin_packs_dir() / "tiers.yaml")
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
