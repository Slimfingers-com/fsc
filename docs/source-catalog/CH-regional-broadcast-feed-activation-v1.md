# Switzerland regional broadcast feed activation review v1

Review date: 2026-09-30

## Scope

This review covers the 12 already-approved Swiss regional broadcast Sources.
No new Sources are introduced.

Runtime semantics:

- SourceType: `REGIONAL`
- CoverageScope: `REGIONAL`
- feed class: `news`
- default confirmation role: `editorial`
- Tier 1 feeds are active
- programmes and language variants remain SourceOutlets
## Tier 1: activated

- Léman Bleu — News régionales
  - `https://www.lemanbleu.ch/documents.rdf?idz=31&cids=10732`
- Canal 9 / Kanal 9 — Canal9
  - `https://canal9.ch/feed/`

Both endpoints are officially exposed by the current publisher sites and were
validated on 2026-09-30 as current parseable RSS feeds with regional editorial
news items. Canal9 carries both French- and German-language regional output.
## Reviewed but not activated

- TeleBärn, Tele M1 and TVO: current official sites contain regional news/video
  output but expose no stable public RSS/Atom newsroom feed.
- TeleTicino: current official site contains TicinoNews/video output but no
  stable public RSS/Atom newsroom feed was established.
- Radio Central, Radio Grischa, Radio Chablais and Radio BeO: current sites
  expose radio/editorial content but no stable public article-news RSS/Atom feed
  was established.
- RadioFr. Fribourg/Freiburg exposes multiple podcast RSS feeds, including
  hourly news audio. Audio/podcast feeds are not substituted for an article-news
  feed in this catalog.
- Radio Ticino exposes a generic site feed, but current entries are primarily
  station formats, promotions and competitions; its Radiogiornale feed is audio
  and is not substituted for an article-news feed.

No feed URL is inferred from undocumented patterns.
## Identity and ingestion rules

- Shared ownership does not merge independently licensed regional editorial
  Sources.
- Canal 9 / Kanal 9 remains one bilingual Source with language-specific outlets.
- Catalog inclusion without a reviewed feed remains catalog-only.
- Existing SRF/RTS/RSI/RTR regional output remains within the already-existing
  national language-region Sources.
- Reconciliation remains dry-run-first, fail-closed and transactional.
