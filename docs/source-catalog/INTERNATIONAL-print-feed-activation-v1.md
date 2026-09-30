# International print feed activation review v1

Review date: 2026-09-30

## Scope

This review covers the already-curated 35-title international print
meta-catalog outside the United States and Europe. No new Sources are introduced
and the Germany-focused shortlist remains unchanged.

Runtime semantics follow ADR 0032:

- `runtime_country_policy: per_entry_required`
- each materializable Source keeps its reviewed ISO country
- SourceType: `NEWS`
- default CoverageScope: `NATIONAL`
- feed class: `news`
- default confirmation role: `editorial`
- Tier 1 feeds are active
- feedless titles remain catalog-only

## Tier 1: activated

The following eight general newsroom feeds were validated as current parseable
RSS/Atom channels and were also verified from the production Hetzner host:

- CartaCapital — `https://www.cartacapital.com.br/feed/`
- The Sydney Morning Herald — `https://www.smh.com.au/rss/feed.xml`
- National Post — `https://nationalpost.com/feed/atom`
- Reforma — `https://www.reforma.com/rss/portada.xml`
- The Jerusalem Post — `https://www.jpost.com/rss/rssfeedsfrontpage.aspx`
- Sabah — `https://www.sabah.com.tr/rss/anasayfa.xml`
- O Globo — `https://oglobo.globo.com/rss/oglobo`
- The Times of India — `https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms`

These feeds represent the publication/newsroom channel. They do not create new
digital Sources separate from the reviewed print Source identity.

## Tier 2: reviewed but production-inactive

- Business Day — `https://www.businessday.co.za/arc/outboundfeeds/rss/`
  remains catalogued but inactive. The endpoint parsed during review, but the
  production worker and a direct reproduction with FSC's normal anonymous
  `FeedFetcher` both returned HTTP 429 on 2026-09-30. No alternate User-Agent,
  throttling bypass or other site-specific workaround is introduced.

## Reviewed but not activated

- The Hindu exposes a current official general RSS feed locally, but the
  production Hetzner host receives HTTP 403. No bypass or alternate user-agent
  workaround is introduced.
- Sözcü exposes a current official RSS feed, but the production feed currently
  contains roughly 640 entries spanning about two days. It remains inactive in
  this first pass rather than introducing a disproportionately large recurring
  ingestion window without an explicit operational policy.
- Mail & Guardian exposes current RSS/Atom feeds, but the general stream mixes
  editorial stories with job advertisements. No narrower clean general-news
  channel was established in this review.
- The Globe and Mail homepage exposes podcast RSS links rather than a verified
  general article-news feed; podcast feeds are not substituted for newsroom
  article ingestion.
- Other shortlisted titles remain feedless where no stable current official
  general newsroom RSS/Atom endpoint was established. Historical RSS pages,
  article links and guessed URL patterns are not enough for activation.
- Sites returning HTTP 403 at homepage or feed level are not worked around merely
  to increase coverage.

## Identity and ingestion rules

- International remains one relevance-weighted meta-catalog rather than being
  split into country catalogs.
- ISO country is preserved per Source; no pseudo-country such as
  `INTERNATIONAL` is introduced.
- The political research groups and external provenance records are unchanged
  by feed activation.
- State/party control metadata remains separate from SourceType and political
  classification.
- A print publication and its web newsroom remain one Source; the feed is only
  an ingestion channel.
- Reconciliation remains dry-run-first, transactional and fail-closed.
