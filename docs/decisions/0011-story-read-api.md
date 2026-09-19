# ADR 0011: Story Read API

## Status

Accepted

## Context

Story clustering creates durable active Story identities and append-only StoryArticle membership history. FSC needs a public read model that exposes the current story state without leaking superseded memberships or inactive source content.

Persisting derived story titles, counts or activity timestamps on `stories` would duplicate information already represented by active memberships and would require additional synchronization during every clustering, reprocessing, source deactivation and cleanup transaction.

## Decision

FSC exposes two read endpoints:

- `GET /stories` returns paginated active story summaries.
- `GET /stories/{story_id}` returns one active story with its current articles, sources, entities and topics.

The read model is derived from active eligible memberships. A membership is eligible only while the membership, story, article, feed and source are not soft-deleted, the feed and source are active, and the article remains normalized.

Story summaries expose a deterministic representative title from the newest eligible membership, language, article/source counts and the first/last article timestamps.

The list endpoint supports:

- language;
- source ID or source slug;
- publication interval;
- entity ID or entity type;
- topic ID or topic slug;
- minimum article count;
- minimum source count;
- `newest`, `oldest` and `largest` sorting;
- stable page/page-size pagination.

Membership-level filters select stories containing at least one eligible article matching all supplied membership-level constraints. Summary counts and timestamps still describe the complete active story rather than only the matching subset.

The detail endpoint uses a constant number of PostgreSQL queries rather than relationship-driven N+1 loading. It exposes current articles with their source and clustering evidence, plus source counts and aggregated active entities/topics with the number of story articles in which each occurs.

No additional database columns are introduced for derived metadata. This keeps clustering writes normalized and prevents stale duplicated title/count/timestamp state.

## Consequences

Story reads always reflect the current active clustering state and source eligibility.

Soft-deleted or inactive content disappears from the read API without destructive history deletion.

List queries perform aggregation in PostgreSQL and detail query count does not grow with story size.

If derived story metadata later becomes expensive enough to require materialization, that must be introduced as an explicitly maintained read model rather than ad-hoc columns on `stories`.
