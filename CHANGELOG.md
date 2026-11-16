# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

### Added
- Engine: section ingest for Markdown, PDF and Word; decision extraction one section per prompt; rule packs with supersede, tighten and waive precedence; tag, scope, data-class and tier selection; verbatim quote verification; interactive walk-through with challenge mode; maturity levels for observability, alerting and resilience; compliance traceability; Markdown and JSON record; per-prompt manifest.
- Rule packs: 118 approved rules across industry (reliability, resilience, recovery, scalability, observability and service levels, security, service-to-service auth, PCI DSS data handling, cost), six author packs and the practice pack. Every rule carries a source and licence.
- Skill for Claude Code and Codex with three standard-library scripts and the packs synced as JSON.
- Seed compiler for PDF, Markdown and YAML, with a rule-by-rule approval command.
- Eval corpus of three documents with expected findings, a scoring runner and a CI plumbing gate.
- Spec exported as JSON schemas, docs site, decision records, attribution and notice files.
- Evidence policy: decision proposals and findings must quote the text; near-miss quotes are snapped to the real sentence with number and length guards; failures without a quote are kept as unverified; passes without a quote are dropped.
- Judging in batches of a few rules per prompt so small models answer every rule.
- Tag families: a decision tagged with a specific concern (`metrics`, `backup`, `timeout`, `auth`) also matches rules tagged with its family (`observability`, `recovery` and `data`, `resilience`, `security`), in the engine and the skill script alike.
- Judge prompts ask for the explanation before the verdict and treat an absent requirement as a fail, not unclear.
- A fourth verdict, `n/a`: the judge decides whether a rule's concern is settled by this decision at all, so a database choice is not failed for saying nothing about retries. Not-applicable findings are counted in the record, not listed, and never lower a maturity level.
- Eval runner: `--out` keeps records, `--only` runs one document, and expected decisions accept any-of keyword slots.

### Changed
- Evidence policy: a failure whose quote is not in the text is now kept as unverified with the quote removed, instead of being dropped. A pass with an ungrounded quote is still dropped.

### Known limits
- Small local models (3B class) quote rules instead of the document and therefore produce almost no verified passes. Use 7B or larger.
