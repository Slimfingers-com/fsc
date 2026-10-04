# ADR 0045: Production Claim Embeddings

## Status

Accepted.

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

## Decision

FSC activates OpenAI embeddings for claims only as the next production recall
improvement.

The first provider is text-embedding-3-small on the normal global OpenAI API
endpoint. Article embeddings remain disabled for this rollout. Story clustering
therefore does not gain a new semantic input merely because claim embeddings are
activated.

The embedding provider supports configurable output dimensions. Before persistent
backfill, FSC evaluates 256, 512 and 1536 dimensions against the already reviewed
Luna shadow claim-pair sample. The permanent dimension is selected from empirical
equivalent/non-equivalent separation rather than from model defaults.

Activation is staged:

1. enable the embedding model and /v1/embeddings permission in the FSC OpenAI
   project while retaining the existing hard spend limit;
2. run the dimension evaluation read-only with no database persistence;
3. select the smallest dimension that preserves acceptable separation and recall;
4. run a small claim-only persistent batch and review claim-group effects;
5. only then allow the normal worker to backfill the remaining claims at a bounded
   batch rate.

No article embeddings are persisted during this rollout. Luna remains shadow-only,
and ADR 0042 relation semantics are unchanged.

## Cost and storage guardrails

The production corpus at decision time contains about 150k active claims and about
17 million claim-text characters. API cost for one full claim backfill is therefore
small relative to the existing $5 project hard limit, but vector storage is not:
1536-dimensional PostgreSQL float arrays would require roughly 1.85 GB of raw vector
payload for claims alone before row/TOAST overhead.

For that reason, using the provider default dimension without evaluation is
explicitly rejected. The rollout must record claim embedding coverage in the
production quality report.

## Consequences

Claim grouping can use the semantic path that already exists in
RuleBasedClaimRelationAnalyzer, improving paraphrase recall without lowering the
lexical threshold globally.

Provider/model/dimension changes remain auditable through processing identity and
cause normal reprocessing.

Article-level semantic clustering is a separate future decision. This ADR does not
activate it.
