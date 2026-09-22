# ADR 0018: Integrated Story Analysis API

## Status

Accepted

## Context

Stories #9 through #12 persist independently versioned analysis outputs:

- Claim Groups and explicit contradictions;
- Evidence and claim-group evidence links;
- Consensus and Difference summaries;
- Coverage summaries, Coverage Gaps and Missing Perspectives.

Consumers should not need to reconstruct those relationships themselves. At the same
time, composing the latest row from each table independently could mix generations
that were never valid together.

## Decision

FSC adds one read-only integrated endpoint:

- `GET /stories/{story_id}/analysis`

The endpoint is a composition layer, not a new analysis pipeline. It introduces no
new processing state, worker or persisted analysis generation.

The response contains:

- explicit processing-run IDs for Claim Relations, Evidence, Consensus and Coverage;
- current Claim Groups and their members;
- current Evidence nested under each Claim Group;
- the current Consensus summary for each Claim Group;
- Missing Perspective state for each Claim Group when present;
- current Difference summaries between contradictory groups;
- current Story Coverage metrics and Coverage Gaps.

The API uses the existing Coverage and Consensus services as the upstream consistency
gate. A response is returned only when the complete current Claim Group, Evidence,
Consensus and Coverage generations are mutually compatible.

In addition, the composition layer verifies that:

- active Claim Groups and relations belong to one Claim Relation processing run;
- active Evidence items and links belong to one Evidence processing run;
- the Consensus generation is the exact current successful Consensus run;
- the Coverage summary references that Consensus run;
- the Coverage processing run is successful and its input hash still matches the
  current Coverage snapshot;
- active Coverage Gaps and Missing Perspectives belong to the same Coverage run.

After composition, the complete Coverage/Consensus snapshot is loaded and hashed again.
The response is returned only when the final input hash, all four generation IDs and
the active Coverage summary are unchanged. This optimistic end-to-end revalidation
detects an upstream commit that occurs while the multi-query response is being built
without holding long-lived global processing locks.

If any invariant or final revalidation fails, or a required downstream generation has
not yet been produced, the endpoint returns 404 with
`Current story analysis is not available.` It does not return a partial or
mixed-generation analysis.

The response includes descriptive confidence values that already exist on Claim Groups
and Evidence links. It does not add a truth, credibility, political-neutrality or
overall analysis score.

## Consequences

Clients get one auditable Story/Debate Analysis document while the underlying
pipelines remain independently reprocessable.

Generation IDs let consumers and auditors identify exactly which persisted runs
produced a response.

A temporary 404 during downstream catch-up is preferred over serving internally
inconsistent analysis.

Future presentation or summarization APIs may build on this endpoint without changing
the persisted analysis semantics.
