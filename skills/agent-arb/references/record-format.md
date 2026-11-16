# Record format

Two files: `<doc>.record.json` holds everything and matches `record.schema.json`; `<doc>.record.md` is the alignment document people read and accept, and it stops after the Summary. Decisions with their findings, document-level findings, advisory answers, compliance traceability and the packs used are in the JSON only.

Markdown order:

1. Title, date, engine ("agent-arb skill"), host model name, tier, and the sentence: "This is a design-time review of what the document states. It is not an assessment or attestation against any compliance framework."
2. Alignment, the page stakeholders accept, in this order: purpose; document name, version, content hash and the sentence that acceptance applies to this revision only; outcome (pending, approved, approved with conditions, not approved); statement; numbered conditions; "Agreed decisions" table (#, decision, chosen, section); "Action items" table (#, action as rule id and title, decision, severity, owner or "(unassigned)", status open/disputed/done); "Disposition summary" of accepted, disputed, revised, waived and open counts; "Approvals" table with exactly the columns Name, Role, Decision, Date. No signature column: a date is the acceptance. Then a horizontal rule and the review detail below.
3. Levels: for observability, alerting and resilience, "observed level N, target level M, missing <rule ids>". Observed level is the highest level at which every selected rule with that level passed.
4. Service levels stated in the document: every sentence mentioning a percentile, availability, error budget, SLO, SLA, RPO or RTO.
5. Summary: decisions reviewed, findings (with how many were judged not applicable), failed by severity, and the sentence naming the JSON file that holds every finding. The Markdown ends here.
