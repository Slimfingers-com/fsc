# ADR 0009: Entity Recognition and Topic Detection

## Status

Accepted

## Context

Normalized articles need reproducible entity mentions and reusable topics without committing the persistence model to one NLP vendor.

## Decision

FSC exposes a SQLAlchemy-free `EntityTopicAnalyzer` contract using immutable dataclasses. The initial `local-rules` provider is deterministic and versioned. A SHA-256 analysis hash covers normalized title/text, language, provider, and version. A polling worker selects eligible active articles with `FOR UPDATE SKIP LOCKED`; each article is committed independently. Provider output is computed before prior associations are replaced, so failures retain the last successful result.

Entities are resolved by normalized name plus type, with aliases considered only inside the same type. Topics use conservative normalization and stable slugs. Soft-deleted canonical records do not block new active records; partial unique indexes enforce active uniqueness. Mention rows retain offsets and permit repeated mentions while PostgreSQL 17 `NULLS NOT DISTINCT` prevents duplicate offset-less mentions.

## Consequences and limits

The local provider recognizes capitalization patterns, organization suffixes, a deliberately small location/event vocabulary, and repeated significant terms/phrases. It does not perform coreference, knowledge-graph linking, deep morphology, or robust uncased-language analysis. Future spaCy, Stanza, transformer, Knowledge Graph, or LLM adapters implement the same contract and increment their version; no service or database coupling is required.
