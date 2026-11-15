"""Run the golden corpus through the engine and score it.

Usage:
  uv run python evals/run_evals.py            # real model from config
  uv run python evals/run_evals.py --fake     # scripted model, checks plumbing only

Metrics per document, then averaged:
- decision_recall: expected decisions found (keyword match on title or evidence)
- finding_recall: must_fail rules that produced a fail finding
- false_positive_rate: must_pass rules that produced a fail finding
- boundary_compliance: every judge prompt carried at most one section
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from agent_arb.cli import run_review  # noqa: E402
from agent_arb.config import load_config  # noqa: E402
from agent_arb.llm import FakeModel, OpenAICompatibleModel  # noqa: E402
from agent_arb.rules import load_builtin_packs  # noqa: E402


def score(doc: Path, expected: dict, model, out: Path) -> dict[str, float]:
    record = run_review(doc, load_builtin_packs(), model, out, int(expected.get("tier", 2)), False, False)
    haystack = [f"{d.title} {d.evidence_quote} {d.chosen}".lower() for d in record.decisions]
    hits = sum(1 for kws in expected.get("decisions_expected", []) if any(all(k.lower() in h for k in kws) for h in haystack))  # noqa: E501
    dec_total = len(expected.get("decisions_expected", [])) or 1
    failed = {f.rule_id for f in record.findings if f.verdict == "fail"}
    must_fail = set(expected.get("must_fail", []))
    must_pass = set(expected.get("must_pass", []))
    manifest = [json.loads(line) for line in (out / f"{doc.stem}.manifest.jsonl").read_text().splitlines()]
    judge = [m for m in manifest if m["step"] == "judge"]
    return {
        "decision_recall": hits / dec_total,
        "finding_recall": (len(failed & must_fail) / len(must_fail)) if must_fail else 1.0,
        "false_positive_rate": (len(failed & must_pass) / len(must_pass)) if must_pass else 0.0,
        "boundary_compliance": 1.0 if all(len(m["sections"]) <= 1 for m in judge) else 0.0,
        "decisions": len(record.decisions),
        "findings": len(record.findings),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--corpus", default=str(ROOT / "evals" / "corpus"))
    a = ap.parse_args()
    if a.fake:
        from conftest import scripted_responder

        model = FakeModel(scripted_responder)
    else:
        cfg = load_config()
        model = OpenAICompatibleModel(cfg.model.base_url, cfg.model.name, cfg.model.api_key, cfg.model.timeout_seconds)
    thresholds = yaml.safe_load((ROOT / "evals" / "thresholds.yaml").read_text())
    results: dict[str, dict[str, float]] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for doc in sorted(Path(a.corpus).glob("*.md")):
            expected = yaml.safe_load(doc.with_suffix(".expected.yaml").read_text())
            results[doc.stem] = score(doc, expected, model, Path(tmp) / doc.stem)
    metrics = ["decision_recall", "finding_recall", "false_positive_rate", "boundary_compliance"]
    avg = {m: sum(r[m] for r in results.values()) / len(results) for m in metrics}
    print(f"\n{'document':<26}" + "".join(f"{m:>22}" for m in metrics) + f"{'decisions':>11}{'findings':>10}")
    for name, r in results.items():
        print(f"{name:<26}" + "".join(f"{r[m]:>22.2f}" for m in metrics) + f"{r['decisions']:>11}{r['findings']:>10}")
    print(f"{'average':<26}" + "".join(f"{avg[m]:>22.2f}" for m in metrics))
    ok = (
        avg["decision_recall"] >= thresholds["decision_recall"]
        and avg["finding_recall"] >= thresholds["finding_recall"]
        and avg["false_positive_rate"] <= thresholds["false_positive_rate_max"]
        and avg["boundary_compliance"] >= thresholds["boundary_compliance"]
    )
    print("\nGATE", "PASS" if ok else "FAIL", f"(model {model.name})")
    if a.fake:
        print("note: the scripted model passes every rule, so finding_recall is meaningless here; this run checks plumbing only")  # noqa: E501
        return 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
