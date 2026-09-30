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

The queue defaults to `review_status=pending` and returns oldest candidates first.
Each item includes the provenance identity, downstream article context,
publisher Source context, upstream Source context, detection method, confidence,
review status and review notes.

Supported filters are:
- review status;
- upstream Source;
- publisher Source;
- detection method;
- provenance relation kind;
- minimum detection confidence;
- creation timestamp lower bound.

Pagination uses bounded `limit` and non-negative `offset`.

## Consequences

The queue is a read-only discovery surface. It never verifies, rejects or
deletes a candidate. Review remains the explicit admin PATCH transition on the existing
ArticleProvenance row. ADR 0036 defines pending, verified and rejected as the
canonical review states.

No confidence threshold is treated as automatic verification. ADR 0020 remains
unchanged: only provenance with review_status=verified influences
source-independence semantics.

Queue queries include only active, non-deleted articles, feeds, publishers and
upstream Sources. Historical provenance rows remain stored even when they are
not actionable in the active review queue.
