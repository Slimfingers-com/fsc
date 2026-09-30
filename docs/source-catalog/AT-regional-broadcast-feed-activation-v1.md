# Austria regional broadcast feed activation review v1

Review date: 2026-09-30

## Scope

This review covers the 19 already-approved Austrian regional broadcast Sources.
No new Sources are introduced and local/micro broadcasters remain outside this
block.

Runtime semantics:

- SourceType: `REGIONAL`
- CoverageScope: `REGIONAL`
- feed class: `news`
- default confirmation role: `editorial`
- Tier 1 feeds are active
- programmes and channels remain SourceOutlets, not additional Sources
## Tier 1: activated

The ORF Open News service explicitly documents RSS feeds for all nine Austrian
regional ORF sites. Each endpoint was validated on 2026-09-30 as HTTP 200,
parseable RSS with 18–20 current items.

- ORF Burgenland — burgenland.ORF.at
  - `https://rss.orf.at/burgenland.xml`
- ORF Kärnten — kaernten.ORF.at
  - `https://rss.orf.at/kaernten.xml`
- ORF Niederösterreich — niederoesterreich.ORF.at
  - `https://rss.orf.at/noe.xml`
- ORF Oberösterreich — oberoesterreich.ORF.at
  - `https://rss.orf.at/ooe.xml`
- ORF Salzburg — salzburg.ORF.at
  - `https://rss.orf.at/salzburg.xml`
- ORF Steiermark — steiermark.ORF.at
  - `https://rss.orf.at/steiermark.xml`
- ORF Tirol — tirol.ORF.at
  - `https://rss.orf.at/tirol.xml`
- ORF Vorarlberg — vorarlberg.ORF.at
  - `https://rss.orf.at/vorarlberg.xml`
- ORF Wien — wien.ORF.at
  - `https://rss.orf.at/wien.xml`
- LT1 — LT1
  - `https://www.lt1.at/feed/`

LT1 advertises its RSS feed directly from the current official homepage. The
feed was validated as standard RSS with current regional editorial/news items.
## Reviewed but not activated

- Kanal3 exposes an official RSS-labelled endpoint, but its XML does not contain
  standard RSS `item` entries; it uses proprietary `sendung/inhalt/bericht`
  elements. FSC does not add a one-off parser merely to raise coverage.
- Radio U1 Tirol advertises a standard site feed, but current entries are mainly
  station news, promotions and events rather than an equivalent regional
  newsroom/article feed.
- W24, RTS Regionalfernsehen Salzburg, Tirol TV, Antenne Steiermark, Life Radio
  and Radio 88.6: current official sites expose editorial/news content, but no
  stable public RSS/Atom article-newsroom feed was established in this review.
- RTV Regionalfernsehen OÖ: no suitable stable public RSS/Atom article feed was
  established; the reviewed live-site hostname also presented a TLS hostname
  mismatch and is not used as a feed workaround.

No feed URL is inferred from undocumented patterns.
## Identity and ingestion rules

- Each ORF Landesstudio remains its own already-reviewed regional Source; its
  television, radio and digital brands remain outlets of that Source.
- The feed represents the regional newsroom/digital editorial output, not a new
  channel Source.
- Catalog inclusion without a reviewed feed remains catalog-only.
- Feed-class metadata remains review/catalog metadata and does not become a
  political classification.
- Reconciliation remains dry-run-first, fail-closed and transactional.
