# ADR 0009: Entity Recognition and Topic Detection

## Status

Accepted

## Context

Normalized articles need reproducible entity mentions and reusable topics without committing the persistence model to one NLP vendor.

## Decision

FSC exposes a SQLAlchemy-free `EntityTopicAnalyzer` contract using immutable dataclasses. The initial `local-rules` provider is deterministic and versioned. The processing identity covers normalized title/text, language, content hash, normalization version, publication time, feed identity, provider, provider version and a configuration identity. The configuration identity includes the service config version, entity/topic confidence thresholds and the maximum number of persisted topics.

A polling worker claims eligible active articles through the generic durable Article-Processing infrastructure. After the claim commits, the article is reloaded from PostgreSQL and the current candidate identity must still match the claim. Provider execution happens outside the final persistence transaction. Immediately before persistence the worker reloads and locks the article again, revalidates both the claim identity and the prepared analysis hash, and only then replaces prior associations. If input changed while the provider was running, the run is skipped and the provider result is discarded. Provider failures retain the last successful result.

Entities are resolved by normalized name plus type. Canonical names and aliases are represented in the indexed `entity_aliases` table; lookup first checks the canonical-name index and then an exact normalized alias/type index. Soft-deleted aliases and entities are ignored. If an alias maps to multiple active entities of the same type, resolution returns no entity rather than choosing arbitrarily. The JSONB alias representation is migrated and removed.

Entity and topic creation uses PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` followed by an exact reload, preserving the outer article transaction during concurrent creation. Topic slugs normally use the readable normalized slug. A genuine slug collision uses the readable slug plus a deterministic hash of the normalized topic name, so distinct Unicode names are not merged.

Worker eligibility is entirely database-queryable. Claims persist input hash, provider, provider version and configuration version together with worker ownership and lease timestamps. Expired leases are reclaimable. Failures increment a persisted attempt counter, release the claim, and schedule bounded exponential retry backoff. Metrics distinguish selected, actually processed, skipped, and failed articles.

Mention offsets are Unicode code-point indexes relative to one explicit `text_source`: `title` references `normalized_title`, and `body` references `normalized_text`. Start is inclusive and end exclusive. Both offsets are null or both present; non-null offsets are non-negative, non-empty, and verified against `mention_text` before persistence. Sentence indexes are field-relative and zero-based. The complete provider result is validated before prior successful associations are deleted.

Soft-deleted `ArticleEntity` and `ArticleTopic` associations, soft-deleted Entity/Topic masters and associations belonging to currently ineligible articles are excluded from APIs, search filters and downstream story features.

## Consequences and limits

The local provider recognizes capitalization patterns, organization suffixes, a deliberately small location/event vocabulary, and repeated significant terms/phrases. It does not perform coreference, knowledge-graph linking, deep morphology, or robust uncased-language analysis. Future spaCy, Stanza, transformer, Knowledge Graph, or LLM adapters implement the same contract and increment their version; no service or database coupling is required.

Configuration changes that alter persisted analysis results automatically change the processing identity and therefore trigger reprocessing.
