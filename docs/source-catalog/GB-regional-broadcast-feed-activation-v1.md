# United Kingdom devolved broadcast feed activation review v1

Review date: 2026-09-30

## Scope

This review covers the six already-approved GB devolved/regional broadcast
Sources. No new Sources are introduced and English local ITV/BBC expansion
remains deferred.

Runtime semantics:

- SourceType: `REGIONAL`
- CoverageScope: `REGIONAL`
- feed class: `news`
- default confirmation role: `editorial`
- Tier 1 feeds are active
## Tier 1: activated

- BBC Scotland — BBC News - Scotland
  - `https://feeds.bbci.co.uk/news/scotland/rss.xml`
- BBC Cymru Wales — BBC News - Wales
  - `https://feeds.bbci.co.uk/news/wales/rss.xml`
- BBC Northern Ireland — BBC News - Northern Ireland
  - `https://feeds.bbci.co.uk/news/northern_ireland/rss.xml`

All three endpoints were validated on 2026-09-30 as current parseable BBC News
RSS feeds carrying devolved-nation editorial news.
## Reviewed but not activated

- STV News: the current official newsroom site carries active Scottish news but
  exposes no stable public RSS/Atom newsroom feed.
- ITV Cymru Wales and UTV: the current ITV News regional pages carry active
  devolved news but no stable public RSS/Atom newsroom feed was established.
  Podcast/video feeds are not substituted for article-news feeds.

No feed URL is inferred from undocumented patterns merely to increase coverage.

## Identity and ingestion rules

- The three BBC nations remain three devolved editorial Sources for FSC regional
  independence counting; radio and television services remain outlets.
- Newyddion S4C remains attributed to BBC Cymru Wales and is not duplicated.
- Catalog inclusion without a reviewed feed remains catalog-only.
- Reconciliation remains dry-run-first, fail-closed and transactional.
