# Ledger Service: design

## Overview

The ledger service records customer payments for the billing team. It is important for revenue.

## Data storage

Payments are written to the shared billing MySQL database that the invoicing service also writes to. Card numbers and the card verification code are stored in the payments table so that retries can be replayed. Backups run nightly to the same server. We have not decided on a retention period.

## Calling other services

The ledger calls the customer service and the fraud service over the internal network, which is trusted, so no authentication is needed between them. Calls use the default client settings. If the fraud service is slow the ledger waits for it.

## Monitoring

We will track average response time and alert when CPU on the ledger hosts goes above 80 percent. The alert goes to the team email.
