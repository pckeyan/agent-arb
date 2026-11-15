# Orders Service: design document

Tier: 1, customer-facing and revenue-bearing.

## Goals and non-goals

Goals: accept orders, charge the card, hand the order to fulfilment within two seconds at p99.
Non-goals: inventory management and refunds are owned by other services.
Quality attributes in priority order: availability, then latency, then cost.

## Storage decision

We considered a shared relational database with fulfilment and a dedicated database per service. We chose a dedicated PostgreSQL cluster for orders because a shared schema would couple our release cycles. The cluster runs in two availability zones with synchronous replication. RPO is zero and RTO is 15 minutes, verified by a monthly restore drill owned by the platform team.

## Service-to-service calls

All calls between orders, inventory and fulfilment go through the service mesh with mutual TLS. Workload identities are issued by SPIRE under the trust domain orders.internal, with certificates valid for one hour and rotated automatically. Authorization is enforced by mesh policy, default deny. Calls to inventory have a 300 ms timeout and are retried twice with exponential backoff and jitter. Reservation is idempotent on the order id.

## Observability

Latency SLO: p99 under 2 seconds measured at the load balancer over a rolling 28 days, with a 99.9 percent availability objective. Request latency is recorded as histograms. Alerts fire on error budget burn rate over one hour and six hour windows and page the orders on-call rotation; each alert links to a runbook.
