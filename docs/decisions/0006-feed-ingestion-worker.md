# ADR 0006: Feed ingestion worker

## Status

Accepted.

## Decision

Due feeds are synchronized by a dedicated long-running worker process. The worker runs an immediate batch after startup, then waits for a configurable polling interval. It delegates feed selection and one-transaction-per-feed execution to `FeedSynchronizationRunner`.

The worker catches unexpected batch-level failures so a transient infrastructure error does not terminate the process. SIGTERM and SIGINT trigger graceful shutdown through a shared stop event.

Configuration:

- `FEED_WORKER_POLL_INTERVAL_SECONDS`, default `60`
- `FEED_WORKER_BATCH_LIMIT`, default `100`
- `LOG_LEVEL`, default `INFO`

The Docker Compose worker uses the backend image and codebase rather than a separate placeholder image. No database migration is required.

## Consequences

The ingestion pipeline is operational without coupling scheduling to the API process. Horizontal scaling is intentionally deferred until feed claiming or locking is introduced; production deployment should run one ingestion worker instance for now.
