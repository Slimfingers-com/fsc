# ADR 0027: Feed-level default confirmation roles

## Status

Accepted.

## Context

Article-level `confirmation_role` is authoritative for Consensus and Coverage,
but SourceType is too coarse to choose the best initial role for every item.

A single institutional Source can expose multiple content feeds with different
functions. For example, the same organization can publish press releases,
research publications, official data and institutional position statements.
Using only the SourceType default would force all of those feeds to start with
the same article role.

At the same time, a feed-level value must not silently reclassify historical
articles when operators change feed configuration.

## Decision

Add nullable `Feed.default_confirmation_role`.

`NULL` means that the feed inherits the existing SourceType default from
ADR 0022.

The role resolution order is:

1. explicit article role;
2. feed `default_confirmation_role`;
3. SourceType default.

The feed value is an ingestion default only. It is applied when a new Article is
created from that feed.

Changing the feed default is deliberately **non-retroactive**. Existing Articles
keep their persisted `confirmation_role`. Feed refreshes also do not overwrite
an existing Article role.

If an existing Article needs a different role, it must be changed explicitly
through the article confirmation-role workflow.

## Content-channel activation convention

SourceType remains a fallback, not a reason to activate every channel of a
Source with the same role.

Before an institutional feed is activated, the concrete channel is reviewed for
its content function. Source catalogs may record a `feed_class` and an
`activation_tier` as **catalog/review metadata only**. Neither field is
persisted on the `Feed` database row at this stage.

The initial feed-class mapping is:

| Feed class | Feed default role | Semantics |
| --- | --- | --- |
| `research_publication` | `expert_analysis` | Studies, papers, reports or analytical publications whose channel is consistently research/analysis. |
| `official_data` | `primary_evidence` | Data, measurements or statistics published by the originating institution. |
| `press_release` | `primary_evidence` | Institutional press releases. They are primary evidence for what the institution states, not independent confirmation of the underlying claim. |
| `news` | `primary_evidence` | Institutional news with the same conservative semantics as press releases. |
| `position_statement` | `advocacy` | Normative demands, positions or campaigning statements. |
| `signal` | `signal` | Discovery/update channels that do not independently confirm a claim. |

A feed is not classified as `research_publication` merely because its Source
is `ACADEMIC` or `THINK_TANK`. A mixed channel containing research,
commentary, external publications, event notices or other materially different
content types must either receive one conservative role that is valid for all
entries or remain inactive until a narrower channel or entry-level
classification is available.

Likewise, a bibliographic feed that aggregates publications whose actual
originating publisher is external must not be treated as an ordinary feed of the
aggregating institution when that would misstate source identity or
independence.

The activation-tier convention is operational planning metadata:

- Tier 1: high FSC relevance and a clean, technically usable official channel;
- Tier 2: relevant but less central, mixed in relevance, lower-volume or
  technically harder;
- Tier 3: catalog/reference Source without active ingestion.

Feed class and activation tier are intentionally not new database enums. They
should become persisted dimensions only if runtime routing, filtering or other
processing needs to depend on them.

## Analysis and staleness semantics

Consensus and Coverage continue to consume only the persisted
`Article.confirmation_role`.

The existing Consensus analysis identity already includes
`Article.confirmation_role`, so an explicit Article role change invalidates the
analysis hash as before.

`Feed.default_confirmation_role` is therefore not added directly to Consensus
or Coverage hashes:

- changing only the feed default does not alter existing article semantics;
- newly created articles persist the resolved role, which is already part of
  downstream analysis identity.

No Consensus/Coverage configuration version bump is required.

## API and schema semantics

Feed create/read/update schemas expose the optional default role.

Source administration exposes admin-protected feed creation and partial update
endpoints for existing Sources. A PATCH that omits `default_confirmation_role`
leaves the current feed value unchanged; an explicit JSON `null` clears the
feed default and restores SourceType inheritance for future Articles.

Existing feed rows require no backfill. Their `NULL` value preserves the
pre-existing SourceType-based initialization behavior.

Catalog-only `feed_class` and `activation_tier` metadata are not accepted by
the runtime Feed API and are not stored in the database.

## Consequences

Feed activation can model content-channel semantics more precisely without
creating duplicate Sources or separate SourceTypes.

Examples:

- an academic research feed can default to `expert_analysis`;
- an organization's official-data feed can default to `primary_evidence`;
- an institutional press/news feed can default to `primary_evidence`;
- a campaign/position feed can default to `advocacy`;
- a discovery-only feed can default to `signal`;
- an editorial feed can default to `editorial`.

Article-level review remains the final authority.
