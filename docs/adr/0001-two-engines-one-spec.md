# 1. Two engines, one spec

Status: accepted. Date: 2026-11-15.

## Context

Agent ARB must run inside coding agents, where the host provides the model and tools, and standalone with a local model for sensitive documents. A skill that shells out to an installed CLI would make the skill depend on a package install and tie both to one runtime.

## Decision

The CLI and the skill are two independent implementations of one flow. What keeps them aligned is a shared spec: JSON schemas generated from the Python models, the rule pack format, and an eval corpus run through both. The skill carries its own copies of the packs as JSON and two standard-library scripts for the deterministic steps.

## Consequences

Two places to change when the flow changes, caught by tests that run the skill scripts against the engine. No install step for the skill. The packs are synced into the skill at release time.
