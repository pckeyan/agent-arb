# Catalog Search

## Approach

We will use Elasticsearch for catalog search. Documents are indexed by a nightly job. The index has three replicas. Search requests have a two second timeout.

## Caching

Results are cached in Redis for five minutes.

## Deployment

The service deploys with the standard pipeline.
