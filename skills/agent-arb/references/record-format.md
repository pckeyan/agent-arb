# Record format

Two files, same content: `<doc>.record.md` for people and `<doc>.record.json` matching `record.schema.json`.

Markdown order:

1. Title, date, engine ("agent-arb skill"), host model name, tier, and the sentence: "This is a design-time review of what the document states. It is not an assessment or attestation against any compliance framework."
2. Alignment, the page stakeholders accept, in this order: purpose; document name, version, content hash and the sentence that acceptance applies to this revision only; outcome (pending, approved, approved with conditions, not approved); statement; numbered conditions; "Agreed decisions" table (#, decision, chosen, section); "Action items" table (#, action as rule id and title, decision, severity, owner or "(unassigned)", status open/disputed/done); "Disposition summary" of accepted, disputed, revised, waived and open counts; "Approvals" table with exactly the columns Name, Role, Decision, Date. No signature column: a date is the acceptance. Then a horizontal rule and the review detail below.
3. Levels: for observability, alerting and resilience, "observed level N, target level M, missing <rule ids>". Observed level is the highest level at which every selected rule with that level passed.
4. Service levels stated in the document: every sentence mentioning a percentile, availability, error budget, SLO, SLA, RPO or RTO.
5. Summary: decisions reviewed, findings (with how many were judged not applicable), failed by severity.
6. Decisions: for each, section, scope, tags, data classes, context, options, chosen, implications, then a table of findings (rule, verdict, severity, disposition, note with the author's rationale) excluding `n/a` findings, which appear as one line "Not applicable to this decision (N): ids", then advisory questions with answers.
7. Document-level findings table and advisory answers.
8. Compliance traceability: framework, reference, rule, decision, verdict, disposition, for every rule with `compliance_refs` that produced a finding.
9. Rule packs used: name, layer, version, content hash, rule count.
