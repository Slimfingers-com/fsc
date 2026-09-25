# ADR 0021: Primary Sources as Evidence, Not Independent Editorial Confirmation

## Status

Accepted

## Context

FSC supports institutional and official material through `SourceType.PRIMARY_SOURCE` and already distinguishes that evidence from independent reporting. A primary source can be the strongest provenance for what an institution said, published or measured, but it is not an independent editorial confirmation of its own assertion.

If primary-source articles were counted like newsrooms in Consensus or Coverage independence, a government statement plus one journalistic report could be misrepresented as two independent confirmations.

## Decision

`PRIMARY_SOURCE` remains a full content and evidence source but is excluded from independent editorial-confirmation counts.

Specifically:

- primary-source articles remain part of story membership and article counts;
- their Sources remain part of total `source_count` and `content_source_count`;
- their evidence remains part of `evidence_item_count` and `evidence_source_count`;
- Evidence continues to classify them as `primary_source` or, for numeric official material, `official_data`;
- they do not contribute to Consensus `independent_source_count`;
- they do not contribute to Coverage `independent_content_source_count`;
- the Coverage limited-independent-content gap uses the same eligibility rule as the persisted Coverage metric.

This rule is source-type eligibility, not dependency collapse. Newsrooms reporting independently on the same official document remain independent unless SourceRelation or verified ArticleProvenance says otherwise.

Consensus and Coverage configuration versions are incremented because this changes analysis semantics. Consensus processing identity also includes source type so a NEWS-to-PRIMARY_SOURCE metadata change invalidates prior Consensus analysis.

No API or database schema change is introduced.

## Consequences

A government release plus one independent newsroom yields one independent editorial confirmation plus primary-source evidence, not two confirmations.

Two independent newsrooms plus the same government release yield two independent editorial confirmations plus primary-source evidence.

A story containing only primary-source material can still expose claims, quotations and official data, but it cannot reach `shared` Consensus solely through the originating institution.

Primary-source material remains visible in descriptive source-type and content-source counts, preserving transparency about what material was observed without inflating corroboration.
