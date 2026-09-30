# ADR 0031: Represent cross-media web outlets with a generic digital publication form

## Status

Accepted.

## Context

FSC distinguishes an outlet's broad `media_category` from its more specific
`publication_form`. The runtime already supports `media_category = digital`,
while `PublicationForm` previously exposed only `digital_native`.

That is sufficient for born-digital publications, but not for web outlets of
broadcast or print Sources. An ORF Landesstudio website, Gothamist within the
integrated WNYC/Gothamist newsroom, or a broadcaster's news website is digital
without being a digital-native publication.
## Decision

Add `PublicationForm.DIGITAL = "digital"`.

Use `digital` for digital/web editions or products of a Source whose editorial
identity is not itself born-digital. Keep `digital_native` for outlets whose
publication form is intrinsically digital-native.

A cross-media digital outlet must also carry `media_category = "digital"`
explicitly when it appears inside a non-digital catalog such as a broadcast
catalog. It must not inherit the catalog's broadcast or print medium.

The database publication-form check constraint is extended accordingly.
## Rationale

Mapping cross-media web products to `digital_native` would encode a false
editorial distinction. Mapping them to `other` would discard information FSC
already models explicitly.

Keeping `digital` and `digital_native` separate preserves the semantic
difference without changing Source identity. Together with ADR 0030, the outlet
is identified by Source, normalized public name and media category; publication
form remains reviewed metadata rather than part of outlet identity.

## Consequences

Regional and future cross-media catalogs can persist real digital outlets
without synthetic names or incorrect digital-native classification.

The migration downgrade converts `digital` publication-form rows to `other`
before restoring the old constraint because the previous schema cannot
represent the new value.
