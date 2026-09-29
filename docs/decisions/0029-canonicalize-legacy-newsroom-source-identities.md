# ADR 0029: Canonicalize legacy newsroom Source identities in place

## Status

Accepted.

## Context

The initial production seed predates the catalog Source-identity model. Two active
German news Sources therefore use distribution-brand identities that are now
modeled as outlets of broader editorial Sources:

- `Deutschlandfunk` is an outlet of the `Deutschlandradio` Source.
- `tagesschau.de` is a distribution outlet of the `ARD-aktuell` Source.

Both legacy runtime Sources already own active Feeds and historical Articles.
Creating replacement Sources and moving those relationships would introduce
unnecessary identity churn and risk breaking references to stable Source and
Feed UUIDs.

The catalog architecture already models cross-media identity explicitly:
programmes, channels and websites are outlets; they do not become independent
Sources merely because they use different distribution forms.

## Decision

Canonicalize the two existing runtime Sources in place.

For the Source with legacy slug `deutschlandfunk`:

- preserve the Source UUID;
- preserve the legacy slug `deutschlandfunk`;
- rename the Source to `Deutschlandradio`;
- set `normalized_name` to the normalized canonical Source name;
- set the Source homepage to `https://www.deutschlandradio.de/`;
- preserve all existing Feeds and their UUIDs;
- add Deutschlandfunk, Deutschlandfunk Kultur and Deutschlandfunk Nova as
  broadcast/radio outlets.

For the Source with legacy slug `tagesschau-de`:

- preserve the Source UUID;
- preserve the legacy slug `tagesschau-de`;
- rename the Source to `ARD-aktuell`;
- set `normalized_name` to the normalized canonical Source name;
- keep `https://www.tagesschau.de/` as the Source homepage;
- preserve all existing Feeds and their UUIDs;
- add tagesschau.de as a digital outlet and Tagesschau, Tagesthemen and
  tagesschau24 as broadcast/television outlets.

The legacy slugs intentionally remain unchanged as stable technical identifiers.
A canonical display name must not force URL/API identity churn.

The correction is performed through an explicit dry-run-first reconciliation
command. It is not an Alembic schema migration and does not run at application
startup.

The reconciler fails closed if:

- a required legacy Source is missing;
- the canonical normalized name belongs to a different Source;
- SourceType, coverage scope, country or language do not match the expected
  identity;
- an existing outlet with the same normalized name has incompatible metadata.

The `--apply` operation uses one database transaction.

## Rationale

The Source UUID is the durable editorial identity already referenced by Feeds,
Articles and downstream analysis. Renaming that row is less invasive than
creating a replacement Source and rewriting relationships.

Keeping the existing slug preserves compatibility for existing API and UI
links while allowing the human-facing Source identity to follow the catalog
model.

Outlet creation makes the distinction between editorial Source and distribution
channel explicit and prepares the runtime for the print/digital/broadcast
catalogs without counting one newsroom multiple times as independent evidence.

## Consequences

Historical Articles remain attached to the same Feed and Source identities.

Existing external or internal references using the legacy slugs continue to
resolve.

Future catalog materialization for `ARD-aktuell` and `Deutschlandradio`
must extend these canonicalized Sources rather than create duplicates.

A future explicit Source-alias model could replace legacy-slug compatibility if
the product needs canonical public slugs, redirects or multiple historical
names. That is not required for the current architecture.
