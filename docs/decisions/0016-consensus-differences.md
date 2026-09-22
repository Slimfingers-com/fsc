# ADR 0016: Consensus and Differences

## Status

Accepted

## Context

Story #9 provides story-scoped claim groups and explicit contradiction relations. Story #10 attaches provenance-bearing evidence to the current claim-group generation. FSC now needs a compact structural view of what independent sources share and where their claims differ.

This stage must not infer objective truth from repetition. Multiple articles from the same owner or source family are not independent agreement.

## Decision

FSC adds the story-scoped `consensus_analysis` pipeline using `StoryProcessingState` and `StoryProcessingRun`.

`StoryConsensusSummary` stores one current summary per active claim group. The initial deterministic provider classifies a group as:

- `single_source`: represented by fewer than the configured minimum number of independent sources;
- `shared`: represented by at least that many independent sources.

Independence is calculated from source provenance. When `Source.ownership` is present, sources with the same normalized ownership are counted once; otherwise the source ID is used.

The persisted summary stores raw explanatory counts: claims, articles, independent sources, evidence items, evidence sources and attributed perspectives. These values are descriptive context only. No truth, credibility or political-neutrality score is computed.

`StoryDifferenceSummary` is derived only from the active `StoryClaimRelation` contradiction generation. It stores the two claim groups plus their independent-source and evidence-source counts. The initial difference kind is `contradiction`.

The processing identity covers active Story memberships, complete active claim-group membership, source ownership/provenance, the active Evidence generation, active Perspective attribution identities, active contradiction relations, and provider/version/configuration.

Consensus processing requires every active grouped claim to have current active Evidence. Provider execution occurs outside the final transaction. Finalization follows the existing coordination lock order and re-reads all upstream state under lock before replacing the prior summary generation.

## Consequences and limits

A shared claim is not declared true. A single-source claim is not declared false. The stage reports structural agreement and explicit differences only.

Copy-chain detection beyond declared source ownership remains outside this story. Coverage gaps and missing perspectives remain Story #12. The integrated debate/story analysis API remains Story #13.
