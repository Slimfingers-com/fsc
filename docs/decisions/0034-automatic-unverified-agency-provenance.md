# ADR 0034: Automatic unverified agency provenance candidates

Status: Accepted  
Date: 2026-09-30

## Context

ADR 0020 makes verified ArticleProvenance authoritative for article-specific
content dependencies. ADR 0033 materializes agency/content-supplier Sources even
when no ingestible public feed exists, so agencies can be referenced as
upstream Sources.

Feed ingestion already receives authorship and some provider/source metadata,
but previously discarded provider metadata and never translated known agency
bylines into ArticleProvenance. As a result, agency Sources were referenceable
but automatic ingestion could not create provenance candidates.

## Decision

Feed ingestion may create ArticleProvenance candidates for a conservative,
explicit alias set of the reviewed agency/content-supplier Sources.

Detection sources are:
- structured feed provider/source metadata, recorded as provider_metadata;
- feed byline/author metadata, recorded as byline.

A candidate is created only when the metadata resolves to exactly one reviewed
agency Source. Conflicting provider and byline matches fail closed and create no
candidate. Agency aliases are matched as normalized complete metadata segments,
not arbitrary substrings.

Automatically detected provenance uses:
- relation_kind: supplied_by;
- upstream_article_id: null;
- a fixed detection confidence reflecting metadata strength;
- verified: false.

Provider metadata has higher confidence than byline metadata. Repeated ingestion
is idempotent through the existing active provenance identity. An article from
an agency's own feed never creates a self-provenance edge.

## Consequences

Automatic candidates are audit/evidence data only. Because ADR 0020 loads only
verified provenance for independence analysis, automatic detection does not
change Consensus or Coverage counts.

Manual or later verification remains required before an agency dependency can
affect independence semantics. Verification is an explicit admin-only state
transition on the existing provenance identity via PATCH; create semantics are
not overloaded. The transition changes only the verified flag and preserves
the original detection method, confidence and evidence. Repeating the same
verification state is idempotent, and an admin may revoke verification by
setting verified=false. Existing verified provenance is never downgraded by
repeated automatic detection.

The alias set is code-reviewed and intentionally small. Adding a new agency or
alias requires an explicit code/catalog review rather than fuzzy entity
matching. Missing agency Runtime Sources cause detection to be skipped rather
than breaking feed ingestion.

Provider metadata is now preserved in ParsedFeedEntry for provenance detection;
it is not persisted as an Article field and does not change article identity.
