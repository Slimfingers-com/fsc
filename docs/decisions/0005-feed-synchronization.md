# ADR 0005: Feed synchronization orchestration

Status: Accepted

## Decision

FSC synchronizes feeds through a dedicated orchestration service:

1. Build a conditional HTTP request from the feed URL, ETag and Last-Modified value.
2. Treat HTTP 304 as a successful synchronization without parsing.
3. Parse HTTP 200 payloads and persist articles idempotently.
4. Update feed success/error metadata consistently.
5. Catch expected ingestion failures and persist them as feed state.
6. Allow unexpected programming or infrastructure failures to propagate.

A batch runner discovers active due feeds and processes every feed in its own database
session and transaction. One malformed or unavailable feed therefore does not roll back
successful synchronization of other feeds.

Repositories and services do not own commits, except the batch runner which is the
explicit job transaction boundary described by ADR-007.
