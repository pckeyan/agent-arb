# Orders Service: design document

Tier: 1, customer-facing and revenue-bearing.

## Goals and non-goals

Goals: accept orders from the web and mobile clients, charge the customer's card, and hand the order to fulfilment within two seconds at p99.

Non-goals: inventory management and refunds are owned by other services and are out of scope here.

Quality attributes in priority order: availability, then latency, then cost. We accept eventual consistency between orders and fulfilment.

## Context

The order flow fans out to the payment gateway, the inventory service and the fulfilment queue. Peak load is 400 orders per second during sales events, and we size for three times that.

## Storage decision

We considered a shared relational database with fulfilment and a dedicated database per service. We chose a dedicated PostgreSQL cluster for orders because a shared schema would couple our release cycles. The cluster runs in two availability zones with synchronous replication and a replication lag alarm at 500 ms. RPO is zero and RTO is 15 minutes, verified by a monthly restore drill owned by the platform team.

## Payment handling

The checkout API receives the card number, expiry and card verification code from the client. We tokenise the primary account number at the edge using the payment gateway's vault so that only a token is stored in the orders database. The card verification code is passed to the gateway in the same request and never written anywhere. Stored tokens are encrypted at rest with keys held in the cloud key management service and rotated yearly. Logs are scrubbed of the account number by a redaction filter in the logging library before shipping.

## Service-to-service calls

All calls between orders, inventory and fulfilment go through the service mesh with mutual TLS. Workload identities are issued by SPIRE under the trust domain orders.internal, with certificates valid for one hour and rotated automatically. Authorization is enforced by mesh policy, default deny, allowing orders to call inventory on the reserve route only.

Calls to inventory have a 300 ms timeout and are retried twice with exponential backoff and jitter. Reservation is idempotent on the order id. If inventory is unavailable, the order is accepted and reservation is retried asynchronously; the user sees a pending state.

## Fulfilment integration

Orders publishes an OrderPlaced event to the fulfilment topic using a transactional outbox, so an order row and its event are written atomically. Consumers deduplicate on the order id. Events are partitioned by customer id to keep a customer's orders in order.

## Observability

Latency SLO: p99 under 2 seconds measured at the load balancer over a rolling 28 days, with a 99.9 percent availability objective. Request latency is recorded as histograms. Alerts fire on error budget burn rate over one hour and six hour windows and page the orders on-call rotation; each alert links to a runbook. Traces are propagated across the mesh with the request id in every log line.

## Open questions

Whether to move the payment gateway call off the synchronous path is undecided, owner: payments lead, by end of quarter.
