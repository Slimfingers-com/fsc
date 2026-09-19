# ADR 0010: Story Clustering

## Status

Accepted

## Context

FSC needs to group eligible normalized articles into reproducible stories while preserving article-level processing history, supporting reprocessing and allowing multiple workers without duplicate active memberships or inconsistent clusters.

## Decision

Story clustering is implemented behind the SQLAlchemy-free `StoryClusterer` provider contract. The initial `local-rules` provider is deterministic and versioned.

A `Story` is the active cluster identity. `StoryArticle` is an append-only processing history with soft deletion for superseded active memberships. PostgreSQL enforces at most one active story membership per article and one membership per processing run.

The clustering input identity includes the raw article title, effective article time, language, title-feature version and normalized title terms, plus the active Entity and Topic IDs. The processing configuration identity covers the service configuration version, title-feature version, clusterer configuration, clustering window and candidate limit. Claims store the complete generic processing identity; after claim commit the current article/features must still match before a result can be persisted.

Candidate discovery only considers active stories and eligible active articles, feeds and sources in the same language and configured time window. Candidate memberships are ranked round-robin by story: the newest matching membership of every story is considered before a second membership from any story. This prevents one high-volume story from consuming the complete candidate limit.

### Concurrency and locks

Cleanup and processing coordinate through one transaction-level PostgreSQL advisory lock namespace.

- Cleanup acquires the global coordination lock exclusively before deactivating ineligible memberships, invalidating their processing identities and deactivating orphan stories.
- Story processing acquires the same global coordination lock in shared mode before heartbeat/finalization.
- Processing then acquires an exclusive partition lock derived deterministically from the article language.
- Articles in the same language are therefore serialized for candidate selection and story mutation, while different language partitions can cluster concurrently.
- The article is re-read after the partition lock is acquired. If its language or processing identity changed while the lock was being acquired, the run is skipped and reclaimed later with the new identity.
- Cleanup cannot race a running clustering transaction because its exclusive global coordination lock conflicts with every processing transaction's shared coordination lock.

The lock order is coordination lock, lease heartbeat, language partition lock, article/story row locks and writes. This prevents the cleanup/processing lock inversion that could otherwise deadlock.

### Reprocessing

Reprocessing always writes a new `StoryArticle` history row.

- If an article remains a singleton and no replacement match is found, its existing Story ID is retained.
- If an article leaves a multi-member story and has no replacement match, it receives a new Story.
- If it matches another active candidate story, membership moves atomically to that story.
- When a move empties the old story, that story is soft-deactivated in the same transaction.
- Cleanup invalidates processed state for memberships that become ineligible, so reactivation of the article/feed/source can claim and cluster the article again.

Provider results are validated before writes: similarity must be finite and within the accepted range, and a returned story must belong to the prepared candidate set and match the article language.

## Consequences

Clustering decisions for one language remain serial and deterministic, but unrelated language partitions can use separate workers concurrently.

Story history remains auditable across retries and reprocessing, while active memberships stay unique.

Changing provider configuration, title-feature version, time window or candidate limit changes the processing identity and triggers deterministic reprocessing.
