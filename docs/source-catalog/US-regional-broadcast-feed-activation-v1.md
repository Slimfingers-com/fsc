# United States regional broadcast feed activation review v1

Review date: 2026-09-30

## Scope

This review covers the ten already-approved representative US regional
broadcast Sources. No new Sources are introduced. The broader local-affiliate
universe remains deferred.

Runtime semantics:

- SourceType: `REGIONAL`
- CoverageScope: `REGIONAL`
- feed class: `news`
- default confirmation role: `editorial`
- Tier 1 feeds are active
- cross-media web brands remain digital SourceOutlets of the same newsroom
## Tier 1: activated

- WHYY News — WHYY News
  - `https://whyy.org/feed/`
- WBEZ Chicago — WBEZ
  - `https://www.wbez.org/rss/index.xml`
- KQED News — KQED News
  - `https://ww2.kqed.org/news/feed/`
- LAist — LAist
  - `https://laist.com/index.atom`
- Spectrum News NY1 — Local Headlines
  - `https://www.ny1.com/services/contentfeed.nyc%7Call-boroughs%7Cnews.landing.rss`
- Spectrum News 1 North Carolina — Local Headlines
  - `https://spectrumlocalnews.com/services/contentfeed.nc%7ccharlotte%7cnews.landing.rss`
All six selected endpoints were validated on 2026-09-30 as current parseable
RSS/Atom feeds with regional newsroom content and were also tested successfully
from the production Hetzner host.

WHYY documents an RSS entry point at `https://whyy.org/rss`; it currently
redirects to the selected `/feed/` endpoint. WBEZ exposes its feed in the
official page metadata. NY1 and Spectrum North Carolina publish dedicated RSS
pages linking the selected local-headline feeds.

## Reviewed but not activated

- WNYC / Gothamist Newsroom: Gothamist exposes a valid current feed locally,
  but the production Hetzner host receives HTTP 403. No bypass is used.
- NJ Spotlight News: `/feed/` is technically current and production-reachable,
  but this review did not establish it as an explicitly exposed/documented
  newsroom feed, so it remains inactive under the no-guessed-feed rule.
- WABE News: current newsroom content is available, but no stable public
  article-news RSS/Atom endpoint was established. Podcast feeds are not used as
  substitutes.
- KUT News: KUT currently advertises a Master RSS Feed, but the corresponding
  machine-readable feed returned zero items during validation. It is therefore
  not activated.
- LAist's separate `/rss/latest-news` representation was not selected because
  the current payload is not well-formed XML; the homepage-advertised Atom feed
  is valid and current instead.

No feed URL is inferred from undocumented URL patterns merely to increase
coverage.

## Identity and ingestion rules

- NPR/PBS membership or programme carriage does not merge regional newsrooms
  into national Sources.
- WNYC/Gothamist remains one integrated Source with radio and digital outlets.
- Spectrum NY1 and Spectrum News 1 North Carolina remain separate regional
  Sources despite common ownership.
- Catalog inclusion without a reviewed feed remains catalog-only.
- Reconciliation remains dry-run-first, fail-closed and transactional.
