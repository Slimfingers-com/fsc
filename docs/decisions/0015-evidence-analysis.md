# ADR 0015: Evidence Analysis

## Status

Accepted

## Context

Story #9 groups equivalent article-scoped claims into story-scoped claim groups and records explicit contradictions between groups. It deliberately does not model evidence support or truth. FSC now needs to expose the concrete material behind a claim group while preserving provenance and auditability.

Evidence is not a truth score. A primary source, study, quotation or independent report can support that a source makes or documents an assertion without establishing that the assertion is objectively true.

## Decision

FSC adds the story-scoped `evidence_analysis` pipeline using the existing `StoryProcessingState` and `StoryProcessingRun` lease infrastructure.

Evidence is represented by two persisted concepts:

- `StoryEvidence` is the provenance-bearing evidence item tied to the source claim, article and source.
- `StoryClaimEvidence` links that item to the current `StoryClaimGroup` with relation `supports` or `context`.

The first provider is deterministic `local-rules`. It classifies evidence as `primary_source`, `official_data`, `study`, `direct_quote`, `press_release`, `independent_reporting` or `context`. Classification confidence describes the provider's classification/link confidence, not source credibility or factual truth.

The SQLAlchemy-free `EvidenceAnalyzer` contract receives only explicit evidence inputs. Future providers may use richer document classification or semantic analysis without changing the persistence or processing semantics.

The processing identity includes the active Story membership generation, active ArticleClaim generation, the complete active StoryClaimGroup/StoryClaimGroupMember generation, article title/text/link/content identity, source identity/type, and the direct-quote signal used by the provider. Provider, version and configuration are included.

Provider execution occurs outside the final write transaction. Finalization uses the same coordination order as claim relations: shared processing coordination lock, story-processing heartbeat, language clustering lock, then Story, StoryArticle, Article, ArticleClaim, StoryClaimGroup and StoryClaimGroupMember locks. The full input identity is recomputed before persistence.

Reprocessing soft-deletes the previous active evidence/link generation only after result validation and final stale-input verification. Historical generations remain auditable.

Read APIs expose:

- `GET /stories/{story_id}/evidence`
- `GET /claim-groups/{group_id}/evidence`

Current reads require the evidence, link, claim group, claim, article, story membership, feed and source to remain active and eligible.

## Consequences and limits

The baseline identifies provenance/evidence categories conservatively from already ingested FSC data. It does not independently verify external documents and does not assign a truth, credibility or consensus score.

Consensus and differences remain Story #11. Coverage gaps and missing perspectives remain Story #12.
