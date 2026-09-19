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

Story summaries expose a deterministic representative title from the newest eligible current article, language, article/source counts and the first/last effective article timestamps. Article titles, links and publication timestamps are read from the current Article row; clustering evidence such as match kind, score and details remains the immutable evidence stored on the active StoryArticle membership.

The list endpoint supports:

- language;
- source ID or source slug;
- timezone-aware publication interval;
- entity ID or entity type;
- topic ID or topic slug;
- minimum article count;
- minimum source count;
- `newest`, `oldest` and `largest` sorting;
- stable page/page-size pagination.

Membership-level filters select stories containing at least one eligible article matching all supplied membership-level constraints. Summary counts and timestamps still describe the complete active story rather than only the matching subset.

The detail endpoint uses a constant number of PostgreSQL queries rather than relationship-driven N+1 loading. It exposes current articles with current publication metadata, their source and clustering evidence, plus source counts and aggregated active entities/topics with the number of story articles in which each occurs.

Search results expose the current active `story_id` when the indexed article has an active membership in an active Story. The field is nullable because search indexing can legitimately complete before story clustering. This gives article-centric discovery a direct link into the Story read model without another lookup API.

No additional database columns are introduced for derived metadata. This keeps clustering writes normalized and prevents stale duplicated title/count/timestamp state. Story page-size defaults and limits are configurable through `STORY_DEFAULT_PAGE_SIZE` and `STORY_MAX_PAGE_SIZE`.

## Consequences

Story reads expose the last committed active clustering membership while resolving mutable article/source metadata and eligibility from current rows. During pipeline reprocessing, clustering evidence can therefore briefly describe the previous committed input until the new membership is committed.

Soft-deleted or inactive content disappears from the read API without destructive history deletion.

List queries perform aggregation in PostgreSQL and detail query count does not grow with story size.

If derived story metadata later becomes expensive enough to require materialization, that must be introduced as an explicitly maintained read model rather than ad-hoc columns on `stories`.
