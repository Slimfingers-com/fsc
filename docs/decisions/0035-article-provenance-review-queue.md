# ADR 0035: Article provenance review queue

Status: Accepted  
Date: 2026-09-30

## Context

ADR 0034 creates conservative, unverified ArticleProvenance candidates from
reviewed agency metadata. The verification transition is intentionally explicit
and admin-only, but article-scoped lookup alone does not provide an operational
way to discover candidates awaiting review.

## Decision

FSC exposes an admin-only, paginated review queue at:

`GET /article-provenance/review-queue`

The queue defaults to `verified=false` and returns oldest candidates first.
Each item includes the provenance identity, downstream article context,
publisher Source context, upstream Source context, detection method, confidence,
verification state and review notes.

Supported filters are:
- verification state;
- upstream Source;
- publisher Source;
- detection method;
- provenance relation kind;
- minimum detection confidence;
- creation timestamp lower bound.

Pagination uses bounded `limit` and non-negative `offset`.

## Consequences

The queue is a read-only discovery surface. It never verifies, rejects or
deletes a candidate. Verification remains the explicit admin PATCH transition
on the existing ArticleProvenance row.

No confidence threshold is treated as automatic verification. ADR 0020 remains
unchanged: only verified provenance influences source-independence semantics.

Queue queries include only active, non-deleted articles, feeds, publishers and
upstream Sources. Historical provenance rows remain stored even when they are
not actionable in the active review queue.
