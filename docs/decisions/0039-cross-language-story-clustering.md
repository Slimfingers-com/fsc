# ADR 0039: Conservative cross-language story clustering

Status: Accepted
Date: 2026-10-02

## Context

ADR 0010 made article language a hard candidate and concurrency partition.
That was safe for the initial corpus, but FSC v1.0 must be able to group
coverage of the same event across languages without turning translation into a
claim or weakening false-merge protection.

FSC already stores article language, semantic embeddings when available,
canonical Entity IDs, Topic IDs and immutable StoryArticle match evidence.
Story language is already derived as a single language or `mul` for a mixed
story.

## Decision

Article language remains descriptive metadata, but is no longer a hard Story
boundary.

Candidate discovery is conservative:
- with a compatible semantic embedding, candidates may come from any language
  inside the configured time window;
- without semantics, normal title/entity/topic overlap remains available for
  same-language candidates;
- without semantics, a different-language candidate is only surfaced through
  shared canonical Entity IDs;
- title overlap or Topic overlap alone never establishes a cross-language
  match.

The rule-based matcher applies stricter cross-language acceptance:
- compatible semantic similarity at the configured semantic threshold is
  sufficient; or
- at least two canonical Entity IDs must be shared and Entity Jaccard
  similarity must be at least 0.50.
- Same-language title/entity/topic rules remain unchanged.

Cross-language match evidence records whether the match crossed languages, the
article/candidate language pair and the accepted match basis. The normal
similarity components remain stored as before.

Semantic embeddings remain optional. FSC therefore has useful cross-language
behavior without making an external embedding service a hard runtime
dependency. Entity-only recall is deliberately conservative. `pgvector` and
vector KNN candidate search are not introduced until production evidence shows
the bounded candidate set is insufficient.

## Concurrency

Language-specific advisory locks are replaced by one transaction-level Story
mutation lock. Story clustering and downstream finalizers that require stable
Story membership acquire this same lock.

The existing global coordination lock remains separate:
- processing/finalization holds it in shared mode;
- cleanup holds it exclusively.

The lock order is therefore coordination lock, lease heartbeat where
applicable, global Story mutation lock, then Story/StoryArticle/Article and
analysis row locks. Story rows, the clustered Article row and downstream
Article stabilization locks use `FOR NO KEY UPDATE` rather than `FOR UPDATE`:
FSC mutates or stabilizes their non-key data but never their identity keys, and
the weaker row lock remains compatible with PostgreSQL `KEY SHARE` locks taken
by concurrent processing-state and analysis foreign-key work. This avoids lock
convoys in which a Story/downstream finalizer holds the global mutation lock
while waiting on unrelated article-pipeline transactions.

This intentionally trades some parallelism for deterministic cross-language
membership decisions in v1.0. It avoids races where articles in different
languages concurrently create or mutate Stories that are now allowed to be
shared.

## Consequences

A Story containing one article language keeps that language code. A Story with
multiple article languages is refreshed to `mul`.

Different-language articles with only similar words or broad Topics remain
separate. Two strong canonical Entity matches can connect a story without
embeddings; semantic embeddings can connect translated or paraphrased coverage
when lexical overlap is absent.

Candidate ranking remains bounded, round-robin by Story and deterministic.
Existing tie-breaking by score, newest candidate membership and Story ID is
unchanged.

This ADR supersedes ADR 0010 only where ADR 0010 requires same-language
candidate discovery, language-derived clustering locks or same-language target
validation. Its auditability, processing identity, reprocessing and cleanup
rules remain in force.
