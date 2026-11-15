# Acme platform standards

These are fictional company standards used to demonstrate compiling a seed document.

## Reliability

- Every tier 1 service must run in at least three availability zones.
- Services must publish a readiness endpoint that checks dependencies.

## Security

- All internal traffic must use mutual TLS issued by the Acme platform CA.
- Secrets must be read from Acme Vault; environment variables holding secrets are not allowed.
- Tokens between services must never live longer than 15 minutes.

## Observability

- Latency objectives must be stated as p99 over 30 days.
- Every paging alert must link to a runbook in the Acme runbook catalogue.
