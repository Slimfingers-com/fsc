# Agency automatic provenance detection review v1

Review date: 2026-09-30

## Scope

This review covers automatic provenance hints for the nine already-approved
agency/content-supplier Runtime Sources. It does not add Sources, feeds or
static dependency relations.

Reviewed aliases include the canonical names and conservative common forms for:
dpa, dts Nachrichtenagentur, APA, Keystone-SDA, PA Media, Reuters, Associated
Press, AFP and REGIOCAST Nachrichten.

## Detection policy

Structured provider/source metadata is preferred over byline metadata.
Known aliases must match a complete normalized metadata segment. Arbitrary
substring matching is not used.

If provider and byline identify different agencies, no candidate is created.
If the identified agency Runtime Source is missing/inactive, ingestion
continues without creating provenance. Self-provenance is never created.

All automatic candidates are:
- relation_kind = supplied_by
- verified = false
- upstream_article_id = null
- detection_method = provider_metadata or byline

Provider metadata uses confidence 0.95; byline detection uses confidence 0.90.
These are detection-confidence values, not verification or independence
weights.

## Independence semantics

ADR 0020 remains unchanged: only verified ArticleProvenance affects Consensus
and Coverage independence. Automatic candidates therefore have no immediate
effect on independent-source counts.

Repeated ingestion is idempotent and cannot duplicate the same active
article/upstream-source/relation identity. Existing verified provenance is
preserved.

Verification is performed separately through the admin-only provenance PATCH
transition. Only the verified flag changes; detection method, confidence,
relation identity and evidence remain intact. The transition is idempotent and
may also revoke a previous verification.

## Feed parsing

RSS/Atom author metadata continues to populate the article author field.
Structured entry source/provider metadata is additionally retained in the
ParsedFeedEntry ingestion DTO solely for provenance detection. It is not added
to Article identity and is not persisted as a separate Article column.


## Historical rollout

Articles stored before automatic detection can be reviewed with the same
conservative byline detector through
`scripts/backfill_agency_provenance.py`. Dry-run is the default and
`--apply` is required to persist candidates.

Historical backfill uses only stored article author/byline metadata; provider
metadata from past feed documents is deliberately not inferred. All inserted
rows remain unverified and use the same active provenance identity as live
ingestion, so applying the backfill repeatedly is idempotent.
