# Europe print feed activation review v1

Review date: 2026-09-30

## Scope

This review covers the already-curated 50-title European print meta-catalog
outside DE, AT, CH and GB. No new Sources are introduced and the existing
relevance-weighted shortlist is unchanged.

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

The following 14 newsroom feeds were established through current official
site metadata or an official publisher RSS directory, parsed successfully with
current content, and were also verified from the production Hetzner host.

- Le Monde — `https://www.lemonde.fr/rss/une.xml`
- El País — `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada`
- la Repubblica — `https://www.repubblica.it/rss/homepage/rss2.0.xml`
- Gazeta Wyborcza — `https://wyborcza.pl/pub/rss/najnowsze_wyborcza.xml`
- De Groene Amsterdammer — `https://www.groene.nl/feed.atom`
- HVG — `https://hvg.hu/rss`
- Efimerida ton Syntakton — `https://www.efsyn.gr/feed/`
- Danas — `https://www.danas.rs/feed/`
- NRC — `https://www.nrc.nl/rss/`
- Dagens Nyheter — `https://www.dn.se/rss/`
- Hospodářské noviny — `https://hn.cz/?m=rss`
- Delo — `https://www.delo.si/rss`
- El Mundo — `https://www.elmundo.es/rss/googlenews/portada.xml`
- Jyllands-Posten — `https://newsletter-proxy.aws.jyllands-posten.dk/v1/latestNewsRss/jyllands-posten.dk?count=10`

For Jyllands-Posten the current latest-news channel is used instead of its
top-stories or most-read feeds so ingestion is not biased by publisher ranking.
## Reviewed but not activated

- Corriere della Sera exposes an official homepage RSS endpoint, but the
  currently returned feed is stale: sampled items are dated May 2024. A
  parseable but obsolete feed is not activated.
- Rzeczpospolita exposes a current RSS feed that parses locally, but the
  production Hetzner host receives HTTP 403. No bypass is introduced.
- Respekt advertises a current RSS feed locally, but production receives HTTP
  403. The local feed also exposes a very large history window. It remains
  inactive rather than adding a workaround.
- Other shortlisted titles remain feedless where no stable current official
  general newsroom RSS/Atom endpoint was established in this review. Publisher
  pages, article URLs, historical RSS references and guessed URL patterns are
  not sufficient for activation.

## Identity and ingestion rules

- Europe remains one relevance-weighted meta-catalog rather than being split
  into country catalogs.
- ISO country is preserved per Source; no pseudo-country such as
  `INTERNATIONAL` is introduced.
- The political A–F planning groups and external provenance records are not
  changed by feed activation.
- A print publication and its web newsroom remain one Source; the activated
  feed is only an ingestion channel.
- Reconciliation remains dry-run-first, transactional and fail-closed.
