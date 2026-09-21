# ADR 0013: Perspective Attribution

## Status

Accepted

## Context

Claim extraction produces article-scoped factual assertions with exact text provenance. FSC next needs to expose whose voice a claim represents without prematurely inferring political ideology, truth, agreement, contradiction or source-level bias.

Attribution depends on two independently reprocessed upstream products: active `ArticleClaim` rows and active `ArticleEntity` mentions. Perspective processing therefore needs an input identity that changes whenever either upstream generation changes and finalization that cannot persist results against a different claim/entity snapshot than the provider analyzed.

## Decision

Perspective analysis is implemented behind the SQLAlchemy-free `PerspectiveAnalyzer` contract. The initial `local-rules` provider is deterministic, conservative and versioned.

An `ArticlePerspective` is an article-scoped attribution of one active claim. It classifies presentation as:

- `quoted`: a claim is presented as a direct quotation attributed to an identified entity mention;
- `reported`: a claim is reported or paraphrased as an identified entity's statement;
- `unattributed`: the provider cannot make a supported attribution to an existing entity mention.

This stage does not classify political ideology, editorial stance, support/opposition, truth, agreement, contradiction, consensus or source bias.

Attributed results must reference an existing active `ArticleEntity` mention from the same article. The provider returns a mention ID rather than arbitrary holder text or a new entity identity. Persistence derives `holder_entity_id` and exact `holder_text` from that mention. Unattributed results have neither.

Every result stores exact normalized-field evidence provenance: `text_source`, Unicode-codepoint start/end offsets, sentence index, evidence text, confidence, provider/version and analysis timestamp. Provider results are rejected if evidence does not exactly match the current normalized field, does not contain the referenced claim span, or, for attributed results, does not also contain the referenced holder mention.

The processing identity includes current article normalization identity plus every active claim's ID, processing generation, hash, span and extraction metadata, and every active entity mention's ID, processing generation, entity ID, text, span and extraction metadata. Reprocessing either upstream stage therefore changes the perspective input identity even when human-readable text happens to stay the same.

Perspective processing only starts when at least one active claim exists and every active claim still matches the current normalized article text. Entity mentions with concrete offsets must likewise still match current text. This prevents perspective analysis from running against a stale upstream generation after article normalization changes.

The generic durable Article-Processing infrastructure supplies leases, retries and attempt history. Provider execution happens outside the final write transaction. Before persistence, the worker extends the lease, locks the Article, then locks the current active `ArticleClaim` and `ArticleEntity` rows, reloads the complete input and recomputes its identity. Changed or ineligible input is skipped and can be reclaimed with the new identity.

Reprocessing is append-only from an audit perspective. Previously active `ArticlePerspective` rows are soft-deleted only after a new result has passed validation and final stale-input checks. Provider, lease or persistence failures therefore preserve the last successful active perspective generation. A cleanup step soft-deletes active perspective rows whose linked claim is no longer active and invalidates that article's processed perspective identity so a later claim generation can be analyzed cleanly.

Read APIs expose current active perspectives through:

- `GET /articles/{article_id}/perspectives`;
- `GET /claims/{claim_id}/perspectives`;
- `GET /stories/{story_id}/perspectives`.

Reads also require the linked claim, article, feed, source and, for story reads, story membership to remain active and eligible.

## Consequences and limits

The local-rules provider only recognizes explicit reporting language near known entity mentions and quote punctuation. It deliberately falls back to `unattributed` rather than guessing a speaker.

A later provider may improve attribution quality without changing persistence or processing semantics.

Cross-article claim identity, agreement/contradiction, evidence quality, consensus, coverage gaps and missing perspectives remain separate downstream stages.
