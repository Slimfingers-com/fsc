# ADR 0017: Coverage Gaps and Missing Perspectives

## Status

Accepted

## Context

Story #11 exposes structural agreement and explicit differences. FSC also needs to show where the observed source set is thin, where attention signals exist without corresponding content coverage, and where existing claim groups lack attributed perspectives.

Coverage must remain descriptive. It must not infer ideological camps that are not present in the data and must not turn diversity into a political or truth score.

## Decision

FSC adds the story-scoped `coverage_analysis` pipeline using the existing StoryProcessing lease infrastructure.

The stage persists three outputs:

- `StoryCoverageSummary` records source, signal, owner, claim-group, difference and attributed-perspective counts plus source-type, coverage-scope and country distributions.
- `StoryCoverageGap` records only directly observable gap kinds.
- `StoryMissingPerspective` records current claim groups that have no attributed perspective.

The initial deterministic provider supports two story-level gap kinds:

- `limited_independent_content_sources`: fewer than the configured minimum independent non-signal source owners;
- `signal_without_content_coverage`: one or more Signal sources are present while no non-signal content source is present.

A missing perspective is emitted only when an observed current claim group has zero attributed perspectives according to the current Consensus generation. Contradiction relation IDs involving that group are retained as context. No absent ideology, stakeholder class or political position is invented.

Attention signals remain distinct from content sources. Source independence uses normalized declared ownership when available and source ID otherwise.

Coverage processing accepts only a complete, current successful Consensus generation. The upstream Consensus processing run is persisted with the Coverage summary. Current read APIs hide Coverage as soon as a different Consensus generation becomes active.

The processing identity includes current story membership/source metadata and the full current Consensus/Difference generation. Provider execution occurs outside the final transaction; finalization uses the established story coordination and clustering lock order and revalidates the complete identity before replacing prior results.

## Consequences and limits

Coverage distributions are descriptive facts about the configured source universe, not a claim that all missing source types should be present for every story.

Copy-chain detection beyond declared ownership is not introduced here. Broader attention-vs-reporting analytics across stories or external trend systems can build on the persisted source/signal distribution later.

Story #13 composes Claim Groups, Evidence, Consensus, Differences and Coverage into the integrated Story/Debate Analysis API.
