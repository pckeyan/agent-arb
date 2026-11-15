# Record format

Two files, same content: `<doc>.record.md` for people and `<doc>.record.json` matching `record.schema.json`.

Markdown order:

1. Title, date, engine ("agent-arb skill"), host model name, tier, and the sentence: "This is a design-time review of what the document states. It is not an assessment or attestation against any compliance framework."
2. Levels: for observability, alerting and resilience, "observed level N, target level M, missing <rule ids>". Observed level is the highest level at which every selected rule with that level passed.
3. Service levels stated in the document: every sentence mentioning a percentile, availability, error budget, SLO, SLA, RPO or RTO.
4. Summary: decisions reviewed, findings, failed by severity.
5. Decisions: for each, section, scope, tags, data classes, context, options, chosen, implications, then a table of findings (rule, verdict, severity, disposition, note with the author's rationale), then advisory questions with answers.
6. Document-level findings table and advisory answers.
7. Compliance traceability: framework, reference, rule, decision, verdict, disposition, for every rule with `compliance_refs` that produced a finding.
8. Rule packs used: name, layer, version, content hash, rule count.
