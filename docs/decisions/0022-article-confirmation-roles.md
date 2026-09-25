# ADR 0022: Article-Level Confirmation Roles

## Status

Accepted

## Context

Source type and confirmation function are different dimensions.

A newsroom normally publishes editorial reporting, but an individual article can merely
republish primary evidence. A university, think tank, NGO, company or public institution
can publish different kinds of material over time. Therefore source type must not decide
whether a concrete article counts as an independent confirmation.

ADR 0021 introduced a conservative source-type exclusion for PRIMARY_SOURCE. This ADR
replaces that transitional rule with an article-level model.

## Decision

Every Article has a persisted `confirmation_role` with one of these values:

- `editorial`
- `expert_analysis`
- `primary_evidence`
- `advocacy`
- `signal`

Only `editorial` and `expert_analysis` are eligible to contribute to independent
confirmation counts.

`primary_evidence`, `advocacy` and `signal` remain observable content/evidence but
do not count as independent confirmation.

The article role is authoritative. Source type is used only to choose the initial role
when a newly ingested article has no article-specific decision yet:

- NEWS, AGENCY, REGIONAL, ALTERNATIVE -> `editorial`
- ACADEMIC, THINK_TANK -> `expert_analysis`
- PRIMARY_SOURCE -> `primary_evidence`
- NGO, COMPANY -> `advocacy`
- SIGNAL -> `signal`

After creation, normal feed refreshes do not overwrite the article role. An administrator
can read or change it via the article confirmation-role API.

Existing articles are backfilled once during migration using the same mapping.

Consensus and Coverage use `Article.confirmation_role`, not `Source.source_type`, for
confirmation eligibility. Coverage also uses the article role to distinguish signal
material from content coverage.

Source dependency and provenance semantics remain independent of this decision:
eligible articles can still collapse into one dependency component through verified
ArticleProvenance or applicable SourceRelation records.

EvidenceKind is a separate dimension. It describes what kind of evidence an item is;
confirmation_role describes whether the article can act as an independent confirmation.
Neither replaces the other.

Consensus and Coverage configuration versions are incremented because the analysis
semantics change, and both analysis hashes include the article confirmation role.

## Consequences

The same Source can legitimately publish articles with different confirmation roles.

A NEWS article marked `primary_evidence` does not count as an independent confirmation.

A PRIMARY_SOURCE or THINK_TANK article marked `expert_analysis` can count as an
independent confirmation if it is genuinely independent analysis.

A signal article is excluded from content-source coverage even when its SourceType is
not SIGNAL; conversely a SIGNAL Source article explicitly classified as `editorial`
is treated as content.

ADR 0021 remains valid for the product principle that primary evidence must not inflate
corroboration, but its source-type implementation rule is superseded by this ADR.
