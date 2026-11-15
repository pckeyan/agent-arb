# Evals

A golden corpus of short design documents with planted issues and an expected-findings file each. The runner scores decision recall, finding recall, false positive rate and data-boundary compliance, averaged over the corpus, against `thresholds.yaml`.

```bash
uv run python evals/run_evals.py          # real model from your config
uv run python evals/run_evals.py --fake   # plumbing check with the scripted model, used in CI
```

Add a document by writing `corpus/<name>.md` and `corpus/<name>.expected.yaml` with `tier`, `decisions_expected` (keyword groups that must all appear in one extracted decision), `must_fail` (rule ids that must fail) and `must_pass` (rule ids that must not fail).

Small local models score lower than large ones. Record the model name with any score you quote.
