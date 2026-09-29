# Austria editorial and primary-source feed activation review v1

Review date: 2026-09-29

## Scope

This review covers the approved Austrian national Print, Broadcast, Digital and
Primary Source catalogs. Regional broadcast remains outside this activation
pass.

Feed activation remains channel-specific. Catalog inclusion alone does not
materialize a Source. Cross-media entries use the existing Source identity and
may add reviewed outlets without creating duplicate Sources.

## Tier 1: activated

### Print / cross-media editorial Sources

- DER STANDARD
  - `https://www.derstandard.at/rss`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - DER STANDARD officially documents this as its Newsroom RSS endpoint.
- Falter
  - `https://www.falter.at/rss`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - endpoint validated as RSS 2.0.
- Die Presse
  - `https://www.diepresse.com/rss`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - endpoint validated as RSS 2.0.
- Kurier
  - `https://kurier.at/xml/rss`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - endpoint validated as RSS 2.0.

Their Digital catalog entries extend these Sources instead of creating
duplicates.

### Broadcast

- ORF Information
  - `https://rss.orf.at/news.xml`
  - class: `news`
  - role: `editorial`
  - 15 minutes
  - linked from ORF's public website and validated as RSS.
- AUF1
  - `https://auf1.tv/feed/`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - validated as RSS 2.0.
  - AUF1 Digital remains an outlet extension of the same Source.

### Digital-native Sources

- MOMENT.at — `https://www.moment.at/feed`
- eXXpress — `https://exxpress.at/feed/`
- Unzensuriert — `https://unzensuriert.at/feed/`
- Report24 — `https://report24.news/feed/`
- ZackZack — `https://zackzack.at/feed/`

All five endpoints were validated as parseable RSS feeds and use
`news -> editorial`.

## Reviewed but not activated

- profil: the current broad RSS endpoint includes APA-OTS / press-release
  material, so it is not treated as one coherent editorial feed.
- PULS24, ServusTV and oe24: the obvious public RSS/feed paths tested in this
  review did not return a parseable RSS/Atom feed.
- Primary Sources: the Austrian Parliament documents RSS exports for many
  parliamentary searches, but the concrete export URLs are query-generated.
  No stable canonical endpoint has yet been selected for runtime activation.
  Statistics Austria currently promotes mail subscriptions for press releases;
  no stable reviewed RSS endpoint was established in this pass.

The AT Primary Source catalog is therefore marked reviewed for the common
runtime semantics but contains no configured feed. This does not materialize
any Primary Source by itself.

## Runtime identity semantics

- `create_source` entries without reviewed feeds remain catalog-only.
- `extend_existing_source` entries never create a duplicate Source.
- If the canonical Source already exists, reviewed cross-media outlets may be
  reconciled onto it even when the extension has no separate feed.
- If an extension itself has a configured feed, its base Source must already
  exist; otherwise reconciliation fails closed.
- Missing feedless extension bases are staged/skipped rather than forcing
  catalog-only Sources into runtime.
