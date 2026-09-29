# ADR 0030: Scope SourceOutlet identity by media category

## Status

Accepted.

## Context

FSC models one editorial or institutional identity as one `Source` and its
audience-facing products as `SourceOutlet` records. ADR 0019 explicitly allows
one Source to have print, digital and broadcast outlets.

The original database constraint identified an outlet only by
`(source_id, normalized_name)`. That made two outlets with the same public
brand name collide even when they represented different media categories.

This became visible during Swiss cross-media feed activation. A canonical
Source such as Neue Zürcher Zeitung legitimately needs a print outlet and a
digital outlet that both use the public name "Neue Zürcher Zeitung". Inventing
synthetic names such as "NZZ Online" would move technical identity concerns
into editorial catalog data.

## Decision

A SourceOutlet is uniquely identified within a Source by:

`(source_id, normalized_name, media_category)`

The database unique constraint and runtime reconciliation use this identity.
Two outlets of the same Source may therefore share a normalized name when
their media categories differ, for example:

- `Neue Zürcher Zeitung` / `print`;
- `Neue Zürcher Zeitung` / `digital`.

Two outlets with the same Source, normalized name and media category remain a
conflict. Publication form, language, URL, primary state and active state are
reviewed metadata of that outlet identity; incompatible values are not merged
silently.

Cross-media reconciliation must match existing outlets by normalized name plus
media category. This applies both to the source-catalog reconciler and the
legacy Source-identity reconciler.

No existing production rows require a data backfill because the previous
constraint was stricter. The migration only replaces the unique constraint.

## Rationale

Media category is the stable distinction FSC already uses to represent
cross-media products. It preserves the public outlet name while keeping print,
broadcast, digital, agency, primary-source and organization outlets distinct.

Including publication form in the key would be too granular: a reviewed change
to a form classification should remain metadata reconciliation rather than
create a second outlet identity.
Using only the normalized name would contradict the cross-media Source model
and force catalog-specific aliases that do not correspond to real brands.

## Consequences

Existing Sources can materialize same-named print and digital outlets without
creating duplicate Sources or synthetic outlet names.

Same-medium duplicate outlet names remain protected by a database uniqueness
constraint and by reconciliation conflict checks.

A downgrade to the previous constraint is only possible while no Source has
same-named outlets in multiple media categories. Once such rows exist, they
must be reconciled before downgrading because the old constraint cannot
represent them.

ADR 0019's Source/Outlet model and ADR 0028's catalog reconciliation semantics
are interpreted using this medium-scoped outlet identity.
