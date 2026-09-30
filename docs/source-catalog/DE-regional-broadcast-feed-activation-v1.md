# Germany regional broadcast feed activation review v1

Review date: 2026-09-29

## Scope

This review covers the approved German regional broadcast catalog. The catalog
contains state- and multi-state editorial Sources; local city/district broadcast
remains outside this block.

Runtime semantics:

- SourceType: `REGIONAL`
- CoverageScope: `REGIONAL`
- feed class: `news`
- default confirmation role: `editorial`
- Tier 1 feeds are active
- programmes and channels remain SourceOutlets, not additional Sources

## Tier 1: activated

- Bayerischer Rundfunk — BR24
  - `https://nachrichtenfeeds.br.de/rss/nachrichten/seiten/QXAPkQJ`
- Hessischer Rundfunk — hessenschau.de
  - `https://www.hessenschau.de/index.rss`
- Mitteldeutscher Rundfunk — MDR Aktuell
  - `https://www.mdr.de/nachrichten/index~rss2.xml`
- Norddeutscher Rundfunk — NDR.de
  - `https://www.ndr.de/index~rss2.xml`
- Radio Bremen — buten un binnen Nachrichten
  - `https://www.butenunbinnen.de/feed/rss/nachrichten/neuste-nachrichten100.xml`
- Rundfunk Berlin-Brandenburg — rbb24
  - `https://www.rbb24.de/index.xml/feed=rss.xml`
- Südwestrundfunk — SWR Aktuell
  - `https://www.swr.de/~rss/swraktuell/index.xml`
- Westdeutscher Rundfunk — WDR Nachrichten
  - `https://www1.wdr.de/wissen/uebersicht-nachrichten-100.feed`

All eight endpoints were validated as current parseable RSS/Atom feeds. Only one
reviewed newsroom/news feed is activated per Source.

## Reviewed but not activated

- Saarländischer Rundfunk: the obvious current SR news RSS paths tested in this
  review did not return a parseable RSS/Atom feed. Existing SR audio/podcast
  feeds are not substituted for a general article-news feed.
- RTL Nord, RTL WEST and RTL Hessen: no stable public RSS/Atom newsroom feed was
  exposed by the current sites.
- SAT.1 Norddeutschland and SAT.1 Bayern: no stable public RSS/Atom newsroom feed
  was exposed by the current sites.
- ANTENNE BAYERN: current news audio is available for listening/subscription,
  but no equivalent text/article newsroom RSS feed was selected for FSC article
  ingestion.
- FFH Newsredaktion, radio ffn, R.SH and radio SAW: no stable public text/article
  RSS/Atom newsroom feed was established in this review.

No feed is invented from undocumented URL patterns merely to increase source
coverage.

## Identity and ingestion rules

- A regional broadcaster remains one Source even when it operates multiple
  television or radio programmes.
- The selected feed belongs to the Source newsroom, not to a newly created
  programme Source.
- Catalog inclusion without a reviewed feed remains catalog-only.
- Existing local/community and local-affiliate expansion remains deferred.
- Reconciliation stays dry-run-first and transactional.
