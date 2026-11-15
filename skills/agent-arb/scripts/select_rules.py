#!/usr/bin/env python3
"""Select the rules that apply to one decision, or the document-level rules. Standard library only.

Usage:
  select_rules.py --decision decision.json --tier 2 [--company folder]
  select_rules.py --document --tier 2 [--company folder]

Reads the built-in packs from ../rules/*.json, plus any *.json packs in --company
(company layer) and applies precedence: a company rule may supersede, tighten or
waive a base rule by id. Only approved rules are used.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILTIN = os.path.join(HERE, "..", "rules")
LAYER_ORDER = {"base": 0, "company": 1, "project": 2}


def load_packs(folder, layer=None):
    packs = []
    if not folder or not os.path.isdir(folder):
        return packs
    for name in sorted(os.listdir(folder)):
        if name.endswith(".json") and name != "tiers.json":
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                pack = json.load(f)
            if layer:
                pack["layer"] = layer
            packs.append(pack)
    return packs


def apply_precedence(packs):
    rules, shadowed = {}, []
    for pack in sorted(packs, key=lambda p: LAYER_ORDER.get(p.get("layer", "base"), 0)):
        for r in pack.get("rules", []):
            if r.get("status", "approved") != "approved":
                continue
            ov = r.get("overrides")
            if ov:
                target, mode = ov.get("rule"), ov.get("mode")
                if target in rules:
                    shadowed.append((target, r["id"], mode))
                    if mode in ("supersedes", "waives"):
                        del rules[target]
                if mode == "waives":
                    continue
            rules[r["id"]] = r
    return rules, shadowed


def tier_ok(rule, tier):
    mt = (rule.get("applies_when") or {}).get("min_tier")
    return mt is None or tier <= mt


def select(rules, decision, tier):
    out = []
    dtags = set(decision.get("tags", []))
    dclasses = set(decision.get("data_classes", []))
    for r in rules.values():
        if r.get("target", "decision") != "decision":
            continue
        if r.get("scope", "architecture") != "practice" and r.get("scope", "architecture") != decision.get(
            "scope", "architecture"
        ):
            continue
        cond = r.get("applies_when") or {}
        class_match = bool(set(cond.get("data_classes") or []) & dclasses)
        if r.get("tags") and r.get("scope") != "practice" and not class_match and not (dtags & set(r["tags"])):
            continue
        if cond.get("data_classes") and not (set(cond["data_classes"]) & dclasses):
            continue
        if cond.get("tags_any") and not (set(cond["tags_any"]) & dtags):
            continue
        if not tier_ok(r, tier):
            continue
        out.append(r)
    return sorted(out, key=lambda r: r["id"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decision")
    ap.add_argument("--document", action="store_true")
    ap.add_argument("--tier", type=int, default=2)
    ap.add_argument("--company")
    a = ap.parse_args()
    packs = load_packs(BUILTIN) + load_packs(a.company, "company")
    rules, shadowed = apply_precedence(packs)
    if a.document:
        chosen = sorted(
            (r for r in rules.values() if r.get("target") == "document" and tier_ok(r, a.tier)), key=lambda r: r["id"]
        )
    else:
        with open(a.decision, encoding="utf-8") as f:
            decision = json.load(f)
        chosen = select(rules, decision, a.tier)
    slim = [
        {
            k: r.get(k)
            for k in (
                "id",
                "title",
                "type",
                "severity",
                "scope",
                "target",
                "requirement",
                "question",
                "expects",
                "level",
                "tags",
                "compliance_refs",
            )
        }
        for r in chosen
    ]
    print(json.dumps({"rules": slim, "shadowed": shadowed}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
