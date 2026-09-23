# ADR 0019: Provenance-Aware Source Catalog Metadata

## Status

Accepted

## Context

FSC needs a source catalog that can represent materially different media without
turning descriptive metadata into an FSC-authored political score.

The catalog must support:

- media type and publication form;
- country and language;
- ownership and funding;
- historical circulation and audience measurements;
- publisher self-descriptions;
- third-party editorial-orientation classifications;
- academic and media-database classifications;
- dated public-authority classifications;
- relevant court or legal-status records.

Those assertions can disagree and can change over time. A single mutable
`political_orientation`, `radicality` or `reach` column would destroy provenance
and incorrectly imply that FSC had selected one classification as authoritative.

Circulation and digital reach also use different measurement systems and reference
periods. They must not be collapsed into one score or used as an inclusion threshold.

## Decision

### Editorial sources and outlets

`Source` represents the editorial brand, publisher, broadcaster, institution or
other source identity. The existing `SourceType`, `CoverageScope`, country, language, ownership and funding fields remain independent dimensions. An optional `subnational_region` records a constituent country, state, province or comparable first-level region without overloading the ISO country field.

A source may publish through multiple audience products. FSC therefore stores
media form on versionable `SourceOutlet` records instead of forcing one
`publication_form` onto the whole source.

Each outlet records:

- outlet name;
- media category;
- publication form;
- publication frequency;
- optional outlet language and URL;
- whether it is the primary outlet;
- active state.

This supports, for example, one editorial source with a daily newspaper, a Sunday
edition and a website without pretending they are three unrelated editorial sources.

### Classification assertions

FSC stores source classifications as versioned `SourceClassification` records.

Each record contains:

- source;
- classification dimension;
- classification value and optional detail;
- classifier type and classifier name;
- provenance URL;
- reference date;
- optional validity interval;
- retrieval timestamp;
- optional notes.

Supported dimensions include editorial orientation, radicality, media positioning
and legal status.

FSC does not merge conflicting assertions into a single political label. A publisher
self-description and an external academic, media-database, authority or court record
may coexist for the same source.

The UI and downstream analysis must preserve the classifier and date whenever such
a classification is displayed or used.

### Historical source metrics

FSC stores audience and circulation measurements as `SourceMetric` records instead
of mutable fields on `Source`.

Each record may optionally point to a specific SourceOutlet and contains:

- metric kind;
- numeric value and unit;
- metric scope or edition;
- reference period and optional date range;
- measurement body;
- provenance URL;
- audited flag;
- retrieval timestamp;
- optional notes.

Distinct metric kinds include sold circulation, distributed circulation, print run,
print readers, digital unique users, visits, page impressions, paid digital
subscriptions, subscribers, radio daily listeners, radio hourly listeners,
radio market share, TV viewers, TV daily reach and TV market share.

Broadcast audience metrics remain medium-specific rather than being collapsed into
a generic reach value. Percentage market shares are stored as integer basis points
(for example, 1.7% = 170 basis points) so the existing integer metric value model
remains stable while preserving exact measurement semantics in the metric kind,
unit, scope and reference period.

A print circulation value, reader estimate, digital unique-user value, radio
listener estimate and television audience/share value are not interchangeable and
must never be summed or compared as though they were the same measurement.

### Inclusion policy

Circulation, audience size, mainstream status and political position are descriptive
metadata only. They are not source-inclusion thresholds.

Small, radical, system-oppositional or niche publications may therefore be included
when they are relevant to coverage and perspective analysis, subject to the same
technical and provenance requirements as larger sources.

## Consequences

The source catalog can represent disagreement about a source without FSC deciding
which political characterization is true.

Historical changes remain auditable rather than being overwritten.

Coverage and perspective features can later query source attributes and third-party
classifications explicitly while retaining provenance.

Consumers must not treat a classification assertion as an FSC endorsement or rating.

Metrics require a reference period and provenance, so the application can compare
like with like and surface stale data instead of silently mixing measurement periods.

Additional countries, languages and media categories can use the same model without
a Germany-specific schema change.
