# ADR 0032: Multi-country catalog runtime reconciliation

Status: Accepted  
Date: 2026-09-30

## Context

The FSC source-catalog reconciler originally assumed that every runtime-eligible
catalog represented exactly one country. That is correct for the DE, AT, CH, GB
and US catalogs, but not for the deliberately curated Europe and international
print meta-catalogs. Those catalogs use `country: null` at catalog level and
store the ISO 3166-1 alpha-2 country on each Source entry.

Using an artificial shared country would discard source geography. Splitting the
meta-catalogs into one file per country would undo the already-reviewed
relevance-weighted catalog design.

## Decision

Catalog reconciliation supports two explicit country policies:

- `catalog_required` (default): the catalog must contain one valid ISO
  3166-1 alpha-2 country. An entry may omit its country or repeat the same
  country, but may not differ from the catalog.
- `per_entry_required`: the catalog must set `country: null`. Every
  materializable entry must contain its own valid ISO 3166-1 alpha-2 country.

The second mode is opt-in through:

`runtime_country_policy: "per_entry_required"`

Unknown country policies, missing entry countries, non-ISO country codes and
mixed catalog-/entry-country semantics fail closed before reconciliation plans
or writes runtime state.

Coverage scope remains catalog-defaulted, but a materializable entry may set an
explicit `coverage_scope`. The entry value takes precedence over
`runtime_coverage_scope`. Both values must use the existing
`CoverageScope` enum.

## Consequences

- Existing single-country catalogs retain their previous strict behavior
  without requiring metadata changes.
- Europe and international catalogs can preserve their reviewed meta-catalog
  structure while materializing Sources with correct countries.
- Source country remains ISO country metadata; `INTERNATIONAL` is not used as
  a pseudo-country.
- A national default coverage scope can coexist with explicit regional or
  international exceptions in the same meta-catalog.
- Feed activation remains dry-run-first, transactional and fail-closed.
