# ADR 0028: Explicit source-catalog runtime reconciliation

## Status

Accepted.

## Context

FSC now maintains reviewed source catalogs separately from the runtime database.
Catalog inclusion is intentionally broader than active ingestion. In particular,
organization catalogs contain reference-only candidates as well as Sources with
reviewed Tier 1 or Tier 2 content channels.

Automatically importing every catalog entry would collapse that distinction and
would violate the feed-activation policy established by ADR 0027. Performing
catalog import during application startup or through Alembic would also make
deployments mutate business data implicitly.

At the same time, reviewed feed configuration must be transferable to runtime
without manual, error-prone recreation of Sources and Feeds.

## Decision

Catalog-to-runtime materialization is an explicit reconciliation operation.

The reconciliation command:

- is dry-run by default;
- requires an explicit `--apply` flag for database writes;
- receives explicit catalog file paths rather than discovering and importing all
  catalogs automatically;
- materializes `create_source` entries only when they contain at least one
  reviewed configured feed;
- leaves `create_source` entries with an empty `feeds` array catalog-only;
- may materialize an `extend_existing_source` entry without its own Feed when
  it adds reviewed cross-media Outlets to an already existing canonical
  runtime Source;
- keeps a feedless `extend_existing_source` catalog-only when its canonical
  runtime Source does not yet exist;
- requires `existing_source_key` for all extensions and fails closed when an
  extension with its own reviewed Feed cannot resolve the canonical runtime
  Source;
- materializes Tier 1 feeds as active and Tier 2 feeds as inactive, exactly as
  reviewed in the catalog;
- does not persist catalog-only `feed_class` or `activation_tier` metadata;
- never runs automatically at application startup;
- is not an Alembic data migration.

A missing runtime Source is created only for a `create_source` entry that
contains at least one reviewed feed. Its Source identity, country, language and
catalog outlets are used for initial creation.

An `extend_existing_source` entry is resolved by the canonical normalized
Source name while `existing_source_key` remains the required cross-catalog
identity reference. Catalog tests require the extension name to match the
referenced base Source name. An extension never creates a missing Source.
A feedless extension whose base Source is not materialized remains catalog-only.
If the extension itself carries a reviewed Feed, a missing base Source is a
reconciliation conflict because the Feed must not create a duplicate Source.

An existing runtime Source is reused by normalized institutional name. Its
existing business metadata is not silently overwritten. A SourceType mismatch,
incompatible country or incompatible same-named Outlet is a reconciliation
conflict. Newly added extension Outlets are non-primary by default so an
existing primary print, broadcast or digital Outlet is not displaced.

Feeds are reconciled by canonical URL:

- same Source + same URL: update only reviewed runtime Feed fields when needed;
- missing URL on the same Source: create the Feed;
- same feed name with a different existing URL: conflict;
- URL already assigned to another Source: conflict;
- runtime feeds not represented in the catalog are preserved.

The whole `--apply` invocation uses one transaction. Any conflict or runtime
error rolls the operation back.

## Rationale

The catalog remains a research and planning artifact rather than an implicit
production configuration database. A non-empty reviewed feed list is the
explicit bridge from catalog inclusion to runtime materialization.

Matching existing Sources by normalized institutional name preserves the
existing source-identity model and avoids duplicate Sources for brands,
programmes or distribution channels. Matching Feeds by URL respects the global
Feed URL uniqueness invariant.

Dry-run-first operation makes production changes auditable before execution and
allows the same reconciliation to be repeated safely.

## Consequences

Reviewed organization feeds can be deployed consistently across environments
without activating the full source catalog.

Running reconciliation repeatedly is idempotent when runtime state already
matches the catalog.

The reconciler is deliberately conservative: endpoint replacement, SourceType
changes, destructive feed removal and identity merges remain explicit operator
decisions rather than automatic reconciliation behavior.

Future runtime requirements may justify a persisted catalog activation identity
or a richer source registry, but that is not required for the current reviewed
feed activation workflow.


## Extension to editorial and primary-source catalogs

The same explicit reconciliation mechanism applies to reviewed editorial and
primary-source catalogs.

Catalogs without an `organization_type` declare:

- `runtime_source_type` for the SourceType to materialize;
- `runtime_coverage_scope` when the catalog has a defined runtime scope.

Entry-level `source_type`, country and language metadata may still be present,
but the reconciler falls back to the catalog-level runtime metadata when they
are omitted.

Only `create_source` entries may currently carry materializable reviewed
feeds. Cross-media `extend_existing_source` and `reuse_existing_source`
entries remain feedless in this workflow. A canonical Source feed is configured
on exactly one creating catalog entry, avoiding ambiguous cross-catalog feed
ownership.

For print entries that do not define an explicit `outlets` array, the
reconciler materializes the reviewed print publication itself as the primary
outlet using the catalog media category and the entry publication form.

`unclassified_entries` participate in reconciliation under the same rules as
grouped entries. This permits politically unclassified specialist journalism to
be ingested without assigning it to an A-F planning segment.

These additions do not change the dry-run-first, explicit-path, fail-closed or
transactional behavior defined above.
