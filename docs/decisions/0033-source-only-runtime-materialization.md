# ADR 0033: Source-only runtime materialization

Status: Accepted  
Date: 2026-09-30

## Context

FSC normally materializes a catalog Source only when a reviewed ingestion feed
exists. Feedless `create_source` entries therefore remain catalog-only.

Agency and content-supplier Sources expose a different requirement. Their
general news wires are often licensed B2B products rather than stable public
RSS/Atom feeds, but ADR 0020 requires an upstream runtime `Source` for verified
`ArticleProvenance.upstream_source_id`. Creating those Sources ad hoc when the
first provenance observation appears would make runtime identity dependent on
processing order instead of the reviewed source catalog.

Dummy feeds, guessed endpoints and third-party mirrors are not acceptable
substitutes.

## Decision

A `create_source` catalog entry may opt in to feedless runtime materialization
with:

`runtime_materialization: "source_only"`

The reconciler applies these rules fail-closed:

- `source_only` is valid only with `source_action: "create_source"`.
- A `source_only` entry must not configure any feed.
- Unknown runtime-materialization values are rejected.
- Feedless `create_source` entries without the explicit marker continue to
  remain catalog-only.
- Source metadata and reviewed outlets are created normally.
- Reconciliation remains dry-run-first, transactional and idempotent.
- Existing runtime Sources are matched by the normal Source identity rules;
  reviewed source-only outlets can be reconciled without creating feeds.

A later reviewed catalog change may remove the `source_only` marker and attach
a legitimate feed to the same Source identity. No replacement Source is
created.

## Consequences

Agency and content-supplier Sources can exist as stable provenance references
without pretending FSC can ingest their licensed wires directly.

Static supplier capability still does not collapse independence. Per ADR 0020,
only verified article-level provenance changes consensus/coverage independence;
no blanket dependency is inferred merely because a publisher can consume an
agency.

The existing catalog-only behavior remains the default for all other feedless
`create_source` entries.
