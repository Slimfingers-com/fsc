# ADR 0041: Disputed Claim Relations

## Status

Accepted; provider execution architecture extended by ADR 0042.

## Context

FSC already models hard claim-group contradictions with
`StoryClaimRelation.relation_kind = contradicts`. The production corpus now
contains many multi-source stories with several claim groups, but only a very
small number of explicit contradictions.

Review showed that this is partly intentional: the deterministic provider only
creates a contradiction for very similar assertions with opposite explicit
negation. Real reporting also contains competing accounts that cannot safely
be called logical contradictions, for example incompatible measurements,
counts, or descriptions of the same event.

Collapsing both cases into `contradicts` would overstate what FSC has observed.
Conversely, treating every non-equivalent claim as conflicting would create
large numbers of false differences.

## Decision

FSC adds a second story-scoped claim relation:
`disputes`.

`contradicts` remains reserved for the existing high-confidence logical
polarity conflict. `disputes` means that two claim groups contain materially
incompatible reported assertions while FSC makes no determination about which
assertion is true.

The downstream consensus stage preserves the distinction:

- `contradicts` becomes `difference_kind = contradiction`;
- `disputes` becomes `difference_kind = dispute`.

Coverage counts both as observable differences, but fields explicitly named
`contradiction_relation_ids` continue to contain only true contradiction
relations.

The current deterministic claim-relation provider is deliberately unchanged
and continues to emit only `contradicts`. Production calibration showed that
claim text alone is not sufficient for a safe generic dispute detector. Even
very high lexical similarity can compare different events after claim
extraction removes context such as locations or units.

For example, production contained the extracted claims "feiert Messe mit 800"
and "feiert Messe mit 150". Their lexical scaffolds are identical, but the
source articles refer to different masses in Paris and Lourdes. Treating that
pair as a dispute would be incorrect.

A future provider may emit `disputes` when it has sufficient contextual or
semantic evidence. Claim embeddings, contextual entity/event features, or an
NLI/LLM provider are possible implementations, but none is made a hard
operational dependency by this ADR. Production currently has no active claim
embeddings or configured external semantic-model key.

Database constraints, read APIs, integrated story analysis, and the frontend
all expose the two relation/difference kinds explicitly. The UI presents
`dispute` less strongly than `contradiction`.

## Consequences

FSC can now represent conservative disagreement without mislabelling every
competing account as a logical contradiction. Existing contradiction semantics
and API values remain backward compatible.

Recall remains deliberately limited. In particular, differently worded
competing accounts such as "there was no vehicle contact" versus "the vehicle
caused the collision" may remain unclassified until a validated semantic
relation provider is introduced.

This limitation is preferable to inventing disagreement. Neither relation kind
is a truth, credibility, ideology, or source-quality judgment.
