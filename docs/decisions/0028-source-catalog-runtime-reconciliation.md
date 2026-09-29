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
- considers only catalog entries that contain at least one reviewed configured
  feed;
- leaves entries with an empty `feeds` array catalog-only;
- materializes Tier 1 feeds as active and Tier 2 feeds as inactive, exactly as
  reviewed in the catalog;
- does not persist catalog-only `feed_class` or `activation_tier` metadata;
- never runs automatically at application startup;
- is not an Alembic data migration.

A missing runtime Source is created only when its catalog entry contains at
least one reviewed feed. Its institutional Source identity, country, language
and catalog outlets are used for initial creation.

An existing runtime Source is reused by normalized institutional name. Its
existing business metadata is not silently overwritten. A SourceType mismatch
or incompatible country is a reconciliation conflict.

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
