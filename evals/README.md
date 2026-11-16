# Evals

A golden corpus of short design documents with planted issues and an expected-findings file each. The runner scores decision recall, finding recall, false positive rate and data-boundary compliance, averaged over the corpus, against `thresholds.yaml`.

```bash
uv run python evals/run_evals.py          # real model from your config
uv run python evals/run_evals.py --fake   # plumbing check with the scripted model, used in CI
uv run python evals/run_evals.py --out .agent-arb/evals --only ledger-weak   # keep the records, run one document
```

Add a document by writing `corpus/<name>.md` and `corpus/<name>.expected.yaml` with `tier`, `decisions_expected` (keyword groups that must all appear in one extracted decision; a nested list is an any-of slot, so `[dedicated, [postgresql, database]]` matches either wording), `must_fail` (rule ids that must fail) and `must_pass` (rule ids that must not fail).

Small local models score lower than large ones. Record the model name with any score you quote.

## Scores on record

| Date | Model | Decision recall | Finding recall | False positive rate | Boundary | Gate |
|---|---|---|---|---|---|---|
| 2026-11-16 | qwen2.5:7b via Ollama | 1.00 | 0.90 | 0.14 | 1.00 | pass |

The 7B model still fails some rules on a well-designed document by reading them too literally (for example failing a stated RPO and RTO for not being "explicit"), and most of its failures on a weak document carry no usable quote and are shown as unverified. Treat its records as a first pass for a human reviewer.
