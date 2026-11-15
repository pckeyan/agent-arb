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
