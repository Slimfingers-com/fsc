# ADR 0045: Production Claim Embeddings

## Status

Accepted and active in production since 2026-10-04.

## Context

The v1.0 integrated-analysis review found strong precision but limited claim-group
recall. In a current 30-story multi-source sample, only 7 stories contained a
shared claim group. Several obvious paraphrases remained separate because the
production claim corpus had no semantic embeddings at all and the deterministic
claim-group analyzer therefore operated lexical-only.

ADR 0014 anticipated embeddings as the next recall mechanism. ADR 0042 already
defines embedding-assisted equivalence grouping and explicit-negation
contradictions as deterministic Stage 1 behavior.

The existing semantic-embedding worker can embed both articles and claims. Enabling
that path unchanged would also alter story-clustering inputs and would store vectors
for full articles, which is broader than the v1.0 claim-recall problem.

The FSC OpenAI project intentionally retains restrictive limits: a $5 hard spend
limit plus 30k TPM and 2 RPM for the embedding rollout. Production arrival volume
is higher than two articles per minute, so one provider request per article cannot
sustain steady-state ingestion.

## Decision

FSC activates OpenAI embeddings for claims only as the production recall
improvement.

The provider is text-embedding-3-small on the normal global OpenAI API endpoint.
Article embeddings remain disabled. Story clustering therefore does not gain a new
semantic input merely because claim embeddings are active.

### Vector dimension

FSC uses **256 dimensions**.

A reviewed 314-pair claim sample was evaluated at 256, 512 and 1536 dimensions.
The three sizes had materially similar equivalent/non-equivalent separation.
Larger dimensions did not provide a useful quality improvement, while 256
minimizes PostgreSQL storage.

A pure embedding threshold is explicitly rejected. Same-event but
different-proposition claims can have very high cosine similarity. Production
grouping therefore uses the guarded deterministic hybrid defined by
RuleBasedClaimRelationAnalyzer 2.2:

- lexical grouping remains available at its existing threshold;
- same-language semantic grouping requires semantic similarity >= 0.82 and
  lexical overlap >= 0.35;
- numeric and negation compatibility checks remain in force;
- publishing meta-claims are excluded from the semantic grouping path;
- conflicting relative-time markers are excluded;
- existing cross-language semantic grouping remains unchanged.

### Provider-request batching

Semantic embeddings are requested in **multi-article batches**.

A worker pass:

1. claims and validates multiple article processing leases;
2. prepares only stale claim texts;
3. combines whole articles into one provider request;
4. persists returned claim vectors independently per article;
5. preserves per-article processing identity, retry, lease and input-change
   semantics.

The normal worker batch limit is 25 articles. A request is additionally bounded to
24,000 prepared text characters. If the next whole article would exceed that
budget, it is deferred to a later worker pass rather than partially embedded.
A single oversized article is still allowed to proceed alone so it cannot be
starved indefinitely.

The worker runs at a 60-second polling interval. This design keeps the existing
2 RPM / 30k TPM project limits rather than increasing provider limits to compensate
for inefficient request granularity.

### Rollout sequence and evidence

The rollout was staged:

1. embedding permission was enabled while retaining the project spend guardrail;
2. 256, 512 and 1536 dimensions were evaluated read-only;
3. 256 was selected;
4. a one-article claim-only persistence test succeeded;
5. RuleBasedClaimRelationAnalyzer 2.2 guardrails were deployed;
6. a 25-article multi-article production pilot succeeded;
7. the normal semantic worker was enabled for bounded continuous backfill.

The 25-article production pilot completed all 25 article runs successfully with no
skips or failures. Claim vectors were persisted at exactly 256 dimensions and no
article vectors were created. Subsequent automatic worker cycles also completed
25/25 with one HTTP 200 embedding request per cycle and no observed 429 failures.

Downstream integration was verified in production: embedding persistence changes
claim semantic identity, which makes affected claim-relation analysis stale.
Multi-source stories were subsequently reprocessed by local-rules 2.2 after their
embedding timestamps.

Luna remains shadow-only, and ADR 0042 relation semantics are unchanged. Claim
embedding activation does not enable automatic DISPUTES persistence.

## Cost and storage guardrails

The production corpus at decision time contains about 150k active claims and about
17 million claim-text characters. API cost for one full claim backfill is small
relative to the existing $5 project hard limit, but vector storage is not:
1536-dimensional PostgreSQL float arrays would require roughly 1.85 GB of raw
vector payload for claims alone before row/TOAST overhead.

For that reason, using the provider default dimension without evaluation is
explicitly rejected. Claim embedding coverage remains part of production quality
monitoring.

Operational rollback points created for activation include the pre-persistence
database backup and a pre-activation environment backup. Existing backups must not
be deleted by rollout tooling.

## Consequences

Claim grouping now uses a calibrated semantic recall path without lowering the
lexical threshold globally.

Provider/model/dimension changes remain auditable through processing identity and
cause normal reprocessing.

Provider requests scale with bounded batches rather than article count, allowing
the restricted OpenAI rate limits to remain in place while production ingestion
continues.

Article-level semantic clustering is a separate future decision. This ADR does not
activate it.
