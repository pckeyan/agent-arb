# Writing rules

A rule is a YAML object in a pack file. The schema is `spec/rule.schema.json`.

| Field | Meaning |
|---|---|
| `id` | Stable identifier. Prefix by pack, for example `IND-OBS-003` or `ACME-SEC-001` |
| `scope` | `architecture`, `design`, `implementation` or `practice`. A rule fires only on decisions of the same scope; practice rules fire on every decision |
| `target` | `decision` runs once per decision; `document` runs once against the outline |
| `type` | `check` yields a pass or fail with a verbatim quote; `advisory` yields a question the author answers |
| `tags` | At least one tag from the vocabulary in `src/agent_arb/decisions.py` must match the decision's tags, unless scope is practice |
| `applies_when` | Extra conditions: `data_classes`, `tags_any`, `min_tier` (the rule applies to tiers at or above this criticality, where 1 is highest) |
| `level` | Maturity level 1 to 4 for observability, alerting and resilience rules |
| `expects` | Shapes the evidence must contain, for example `percentile`, `window` |
| `compliance_refs` | Framework and reference identifiers, for example `PCI-DSS-v4.0.1 3.5.1` |
| `source` | Where the principle comes from, its licence, and whether any text was adapted |
| `overrides` | For company and project rules: `supersedes`, `tightens` or `waives` a base rule by id |
| `status` | Only `approved` rules run |

Write the requirement so a reviewer could check it from the document alone, and name what the text has to contain. Keep the author's words out of it; cite them instead.

Validate a pack with `agent-arb rules validate path/to/pack.yaml`.
