# ADR 0042: Hybrid Claim-Relation Provider

## Status

Accepted; first semantic adapter selected by ADR 0043.

## Context

ADR 0041 introduced `disputes` as a weaker relation than the existing hard
`contradicts` relation. Production review showed that claim text alone is not a
safe basis for automatically producing disputes: extracted claims can lose event,
location, unit, attribution, or other article context.

At the same time, a purely deterministic relation provider misses materially
competing accounts such as "there was no vehicle contact" versus "the ICE SUV
caused the collision". Embedding similarity alone is also insufficient because it
measures topical or semantic proximity rather than incompatibility.

FSC therefore needs a way to improve relation recall without making a remote AI
service a hard processing dependency or weakening the meaning of existing
contradictions.

## Decision

FSC introduces a provider-neutral two-stage hybrid claim-relation architecture.

Stage 1 remains deterministic. `RuleBasedClaimRelationAnalyzer` continues to own:

- claim grouping;
- exact, lexical and embedding-assisted equivalence grouping;
- high-confidence explicit-negation `contradicts` relations.

Stage 2 is optional. A `SemanticClaimRelationProvider` receives only a bounded set
of plausible cross-source group pairs selected locally. Candidate selection may use
claim overlap, existing claim embeddings and article-title similarity. The provider
also receives bounded article context for both representative claims.

The semantic provider contract classifies each candidate as one of:

- `equivalent`;
- `contradicts`;
- `disputes`;
- `unrelated`;
- `insufficient`.

For this first hybrid version, only a high-confidence `disputes` result may add a
persisted relation. Semantic `contradicts` results are deliberately not promoted to
hard contradictions. This keeps the established `contradicts` meaning deterministic
until a separate decision explicitly changes it.

Candidate selection is cross-source only, bounded by a maximum candidate count and a
minimum local similarity score. The semantic result must exceed a separate dispute
confidence threshold before it is persisted.

The hybrid analyzer fails closed. If the semantic provider is disabled, unavailable,
raises an error, or returns an invalid result, FSC returns the deterministic Stage-1
result. The story-processing run therefore remains useful and does not depend on the
availability of the semantic provider.

Provider identity, version and configuration are included in the normal
claim-relation processing identity. Enabling or changing a semantic provider therefore
causes auditable reprocessing without schema-specific migration logic.

Article title and a bounded claim-adjacent article excerpt are available to contextual
analyzers. They are included in processing identity only for analyzers that declare
that they use article context, so the existing rule-only production path does not
trigger unnecessary reprocessing.

## Production activation

This ADR adds the generic hybrid analyzer and semantic-provider contract. It does not
select or enable a concrete semantic/NLI vendor in production.

Until a concrete provider is configured, the production worker continues to use the
existing deterministic `local-rules` analyzer. This preserves current behavior while
allowing provider adapters to be evaluated independently.

## Consequences

FSC can add disagreement recall incrementally without conflating similarity with
conflict and without turning an external model into a hard availability dependency.

A provider failure cannot remove deterministic contradictions or prevent deterministic
claim groups from being produced.

The bounded candidate stage limits model cost and reduces the chance that unrelated
claim pairs reach a semantic classifier.

The next decision is provider selection and production calibration: local NLI,
OpenAI, Gemini, or another adapter can implement the same contract without changing
the domain model.
