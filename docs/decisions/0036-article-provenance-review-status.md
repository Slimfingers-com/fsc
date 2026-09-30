# ADR 0036: Canonical article provenance review status

Status: Accepted
Date: 2026-09-30

## Context

ArticleProvenance originally stored review state as a boolean `verified` flag.
ADR 0034 introduced automatically detected, unverified agency provenance
candidates, and ADR 0035 introduced a review queue.

A boolean cannot distinguish a candidate that has never been reviewed from one
that was reviewed and rejected. Deleting rejected candidates would destroy
audit history and allow the same detector to recreate them on a later ingest.

## Decision

ArticleProvenance uses one canonical review state:

- `pending`: detected or created, not currently accepted for independence;
- `verified`: explicitly reviewed and accepted;
- `rejected`: explicitly reviewed and rejected.

The persisted `verified` boolean is removed. `review_status` is the only
persisted review truth.

`reviewed_at` is nullable:
- pending rows have `reviewed_at = null`;
- transitions to verified or rejected set `reviewed_at`;
- returning a row to pending clears `reviewed_at`;
- repeating the same state is idempotent and does not rewrite the timestamp.

The admin PATCH endpoint updates `review_status` explicitly. Detection method,
confidence, relation identity and evidence are preserved.

Automatic live detection and historical backfill always create pending rows.
Repeated detection uses the existing provenance identity and never changes an
existing row's review state.

ADR 0020 remains authoritative for independence semantics. Consensus and
Coverage load only provenance whose `review_status = verified`.

The review queue defaults to pending and can explicitly filter pending,
verified or rejected rows.

## Migration

Existing data is migrated without ambiguity:

- `verified = true` becomes `review_status = verified`;
- `verified = false` becomes `review_status = pending`.

For previously verified rows, `reviewed_at` is initialized from the row's
existing `updated_at`. Pending rows receive no review timestamp.

Downgrade maps only `review_status = verified` back to `verified = true`;
pending and rejected both map to false.

## Consequences

Rejected detections remain auditable and do not reappear in the default pending
review queue. No secondary boolean or rejected flag can drift from the
canonical review status.

The API contract changes from `verified` to `review_status` and
`reviewed_at`. This is an intentional internal/admin API migration rather than
keeping two independently writable representations of the same state.
