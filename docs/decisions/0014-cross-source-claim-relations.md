# ADR 0014: Cross-Source Claim Groups and Relations

## Status

Accepted

## Context

`ArticleClaim` is intentionally article-scoped. FSC needs to identify when claims
from different articles in one Story express substantially the same assertion and when
separate assertion groups explicitly contradict each other. Reusing `ArticleClaim`
IDs as global semantic identities would collapse provenance and make reprocessing
unsafe.

This stage is story-scoped rather than article-scoped. It therefore cannot safely use
`ArticleProcessingState` as its lease or processed-identity abstraction.

## Decision

FSC introduces generic `StoryProcessingState` and `StoryProcessingRun`
infrastructure. The first story pipeline is `claim_relations`. It provides durable
leases, bounded retry backoff, attempt history, processed identity, stale-input
detection and lease-loss handling analogous to the existing article-processing
infrastructure.

Claim relation analysis runs behind the SQLAlchemy-free `ClaimRelationAnalyzer`
contract. The initial `local-rules` provider is deterministic and conservative.

Every active eligible `ArticleClaim` in the Story belongs to exactly one active
`StoryClaimGroup` generation. Group membership is therefore a partition of the input
claims. A group represents claims that the provider considers semantically equivalent
for this Story; it is not a global truth object. Agreement is represented structurally
by multiple claims, articles and independent sources in the same group rather than by
persisting pairwise agreement edges.

`StoryClaimRelation` stores relations between groups. This version supports only
`contradicts`. Evidence support and truth assessment are deliberately excluded and
remain downstream concerns.

The local-rules baseline groups exact normalized claims and very high-overlap lexical
variants only when explicit negation polarity and numeric tokens are compatible. It
creates a contradiction only when two group representatives have compatible numeric
tokens, opposite explicit negation polarity and high lexical overlap after negation is
removed. These are provider limitations, not persistence assumptions.

The processing identity covers the active Story, active eligible `StoryArticle`
memberships and their processing generations, current source identities, and the full
active `ArticleClaim` generations including claim IDs, processing runs, hashes,
normalized text, spans, confidence and extraction provider/version. Analyzer provider,
version and configuration are included as well.

Provider execution happens outside the final write transaction. Finalization follows
the established clustering lock order: shared story-clustering coordination lock,
story-processing heartbeat, language partition lock, then Story, StoryArticle, Article
and ArticleClaim row locks. Locking every current Story article coordinates with claim
extraction, which also locks Article before replacing its claim generation; this
prevents an initial or replacement claim generation from appearing as a phantom after
the final snapshot is taken. The complete input identity is recomputed before
persistence.

Reprocessing soft-deletes the previous active `StoryClaimGroup` and
`StoryClaimRelation` generation only after provider output has passed validation and
the final input identity still matches. `StoryClaimGroupMember` history remains
attached to its historical group. Provider or persistence failures preserve the
previous active generation.

Read APIs expose:

- `GET /stories/{story_id}/claim-groups`
- `GET /claim-groups/{group_id}`
- `GET /stories/{story_id}/claim-relations`

Current reads require active groups, claims, story memberships, articles, feeds and
sources. Group summaries expose claim, article and independent-source counts.

## Consequences and limits

Group IDs are story-scoped processing outputs and can change across generations.
Downstream evidence, consensus and coverage stages must include the active group
generation in their own processing identities rather than treating a group ID as a
permanent global identity.

The deterministic baseline intentionally misses paraphrases that require semantic
reasoning. A future embedding or LLM provider can implement the same contract without
changing audit, processing or API semantics.

Consensus, evidence quality, truth, support, coverage gaps and missing perspectives
remain separate downstream stages.
