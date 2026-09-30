# Agency / content-supplier runtime materialization review v1

Review date: 2026-09-30

## Scope

This review covers the already-approved nine-Source agency/content-supplier
core. No new Sources are introduced.

The current official public sites of dpa, dts Nachrichtenagentur, APA,
Keystone-SDA, PA Media, Reuters, Associated Press, AFP and REGIOCAST
Nachrichten were reviewed for general public RSS/Atom newsroom feeds. No stable
general agency-wire feed suitable for FSC ingestion was established.

No guessed endpoint, third-party mirror, podcast feed or publisher reproduction
is substituted for an agency wire.

## Runtime materialization

All nine reviewed Sources use ADR 0033:

- `runtime_materialization: source_only`
- SourceType: `AGENCY`
- no feeds
- one primary `agency / news_agency` outlet per Source
- country is preserved per Source through the multi-country catalog policy
- default CoverageScope: `NATIONAL`
- Reuters, Associated Press and AFP: `GLOBAL`

Materialized Sources:

- dpa
- dts Nachrichtenagentur
- APA
- Keystone-SDA
- PA Media
- Reuters
- Associated Press
- AFP
- REGIOCAST Nachrichten

## Provenance semantics

These Sources exist so reviewed agency provenance can point to stable runtime
Source identities. Their existence does not imply that every downstream outlet
uses agency copy.

No blanket `content_supplier` relation is created between these agencies and
potential consumers. Concrete dependency continues to be represented by
verified `ArticleProvenance` under ADR 0020.

If FSC later obtains or verifies a legitimate ingestible feed for one of these
Sources, that feed can be attached to the same Source identity after normal
review. Source-only materialization is not a separate Source class.
