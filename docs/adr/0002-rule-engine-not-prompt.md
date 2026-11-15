# 2. The deterministic track is a rule engine, not a prompt

Status: accepted. Date: 2026-11-15.

## Context

Company standards must be applied repeatably. A language model is not deterministic.

## Decision

Seeds are compiled once into versioned, human-approved rules. At review time, rule selection is a local tag and scope match, the model only classifies compliance and quotes evidence, and any finding whose quote is not verbatim in the text is dropped before anyone sees it.

## Consequences

Results are traceable to a rule version and a quote. The model's freedom is bounded to a verdict and an explanation. A bad rule is fixed in YAML, not in a prompt.
