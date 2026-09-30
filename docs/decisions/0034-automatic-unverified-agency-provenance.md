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
- review_status: pending.

Provider metadata has higher confidence than byline metadata. Repeated ingestion
is idempotent through the existing active provenance identity. An article from
an agency's own feed never creates a self-provenance edge.

## Consequences

Automatic candidates are audit/evidence data only. Because ADR 0020 loads only
verified provenance for independence analysis, automatic detection does not
change Consensus or Coverage counts.

Manual or later verification remains required before an agency dependency can
affect independence semantics. Verification is an explicit admin-only state transition on the existing
provenance identity via PATCH; create semantics are not overloaded. ADR 0036
makes review_status the canonical review state with pending, verified and
rejected values. The transition preserves the original detection method,
confidence and evidence. Repeating the same review state is idempotent, and an
admin may return a reviewed row to pending. Existing reviewed provenance is
never changed by repeated automatic detection.

The alias set is code-reviewed and intentionally small. Adding a new agency or
alias requires an explicit code/catalog review rather than fuzzy entity
matching. Missing agency Runtime Sources cause detection to be skipped rather
than breaking feed ingestion.

Provider metadata is now preserved in ParsedFeedEntry for provenance detection;
it is not persisted as an Article field and does not change article identity.


## Historical backfill

The same detector may be applied once to already persisted articles whose
stored author/byline metadata predates this feature. Historical provider
metadata cannot be reconstructed because it was not previously persisted, so
the backfill intentionally uses author/byline data only.

The backfill is dry-run-first and transactional. It considers only non-deleted
articles on active, non-deleted feeds and Sources. It creates the same
pending supplied_by candidate identity as live ingestion and therefore
shares the same idempotence constraint. Existing candidates, including reviewed
ones, are never duplicated or downgraded.

The backfill reports detected candidates, planned changes, already-present
identities, missing upstream Sources and skipped self-dependencies before any
production apply.
