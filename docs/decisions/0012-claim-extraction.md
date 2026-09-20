# ADR 0012: Claim Extraction

## Status

Accepted

## Context

FSC needs auditable, article-scoped factual claims before perspective, evidence and coverage analysis can operate on stable processing outputs. Claim extraction must not silently collapse statements from different articles into one supposed truth object, and it must preserve exact source-text provenance.

## Decision

Claim extraction is implemented behind a SQLAlchemy-free `ClaimExtractor` contract. The initial `local-rules` provider is deterministic and versioned. It is intentionally conservative and sentence-oriented; later NLP or LLM providers can implement the same contract.

An `ArticleClaim` is one distinct extracted assertion belonging to one article and one successful `ArticleProcessingRun`. Repeated identical normalized wording within the same article is deduplicated; terminal sentence punctuation is ignored for this within-article identity. The row stores the exact claim text, normalized claim text, a SHA-256 identity, normalized-field source (`title` or `body`), Unicode-codepoint offsets, sentence index, confidence, provider/version and extraction timestamp.

Claims are article-scoped extraction results. This stage does **not** perform semantic cross-article claim identity, agreement, contradiction, consensus or truth assessment. Those are later analysis concerns. This separation prevents claim extraction from turning similar wording into an unsupported global factual identity.

The processing identity covers normalized title/text, language, content hash, normalization version, publication time, feed identity, provider, provider version and configuration identity. Configuration identity includes the service config version, minimum persisted confidence and maximum claims per article.

The generic durable Article-Processing infrastructure supplies claims, leases, retries, attempt history and stale-input protection. Provider execution happens outside the final write transaction. Before persistence the worker extends the lease, reloads and locks the current article, verifies eligibility and recomputes the complete processing identity. Results for stale or ineligible input are discarded.

Provider results are fully validated before active claims are modified. Every claim must use the declared `TextPart`, point to an exact non-empty span in the selected normalized field, use valid non-negative offsets/sentence indexes, and have finite confidence in `[0, 1]`. The persistence step also verifies that the article still matches the prepared input identity and that the supplied processing run is still active, belongs to the same article and exactly matches the claim-extraction input/provider/configuration identity before prior claims are soft-deleted.

Reprocessing is append-only from an audit perspective: previously active `ArticleClaim` rows are soft-deleted only after a new provider result has passed validation and final stale-input checks, then a new generation is written against the new processing run. Provider or persistence failures leave the last successful active claims intact.

PostgreSQL enforces one active claim hash per article and one occurrence of a claim hash per processing run. Claim reads exclude soft-deleted claims and claims belonging to deleted/ineligible articles, feeds or sources. Story claim reads additionally require an active story and active story membership.

## Consequences and limits

The local-rules baseline treats sufficiently substantial declarative normalized-field sentences as claims. It does not split compound sentences into atomic propositions, resolve pronouns, infer implicit claims, classify stance, assess evidence, or determine truth.

Those limitations are explicit provider limitations rather than persistence assumptions. A future LLM or NLP provider can improve extraction quality without changing processing, audit or API semantics.

Cross-source claim matching and consensus must be introduced as a separate versioned stage rather than by reusing `ArticleClaim.id` as a global semantic identity.
