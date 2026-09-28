# Germany feed activation review v1

Review date: 2026-09-28

## Scope

This review covers the first feed-activation pass for the existing German
`ACADEMIC` and `THINK_TANK` source catalogs.

The activation rules are defined by ADR 0027:

- activate concrete content channels, not whole Sources blindly;
- use SourceType only as a fallback;
- record `feed_class` and `activation_tier` as catalog/review metadata;
- persist only the runtime Feed fields, including
  `default_confirmation_role`;
- do not treat mixed or provenance-ambiguous channels as research feeds merely
  because their parent Source is academic or a think tank.

## Tier 1: activated

### DIW Berlin — Pressemitteilungen

- URL: `https://www.diw.de/de/rss_press.xml`
- feed class: `press_release`
- default confirmation role: `primary_evidence`
- scheduler priority: 1
- fetch interval: 60 minutes
- status: active
- verification: the official DIW RSS service lists a dedicated German
  press-release feed; direct parsing returned a valid RSS 2.0 feed.
- rationale: high relevance for German economic and public-policy claims, but a
  press release is evidence for what DIW states, not an independent confirmation
  of the underlying research claim.

### Potsdam-Institut für Klimafolgenforschung (PIK) — Nachrichten

- URL:
  `https://www.pik-potsdam.de/de/aktuelles/nachrichten/nachrichten/rss.xml`
- feed class: `news`
- default confirmation role: `primary_evidence`
- scheduler priority: 1
- fetch interval: 60 minutes
- status: active
- verification: the official PIK communications page exposes the feed for press
  releases and news; direct parsing returned a valid RSS 2.0 feed.
- rationale: high relevance for climate and policy-related claims. The channel
  also contains institutional news, so it is deliberately not classified as
  `expert_analysis`.

### Stiftung Wissenschaft und Politik (SWP) — official German publications

- URL: `https://www.swp-berlin.org/SWPPublications.xml`
- feed class: `research_publication`
- default confirmation role: `expert_analysis`
- scheduler priority: 1
- fetch interval: 60 minutes
- status: active
- verification: SWP's official RSS service distinguishes its broad/general feed
  from feeds containing only official SWP publications; direct parsing of the
  German publications feed returned valid RSS 2.0 entries.
- rationale: this is a narrow institutional analysis/publication channel rather
  than SWP's mixed general feed.

## Tier 2: verified but initially disabled

These channels are official and technically parseable, but are less central to
the initial FSC policy/news evidence focus. They are recorded in the academic
catalog with `active=false` so that their semantics are reviewed and retained
without increasing ingestion volume yet.

| Source | Channel | Feed class | Role |
| --- | --- | --- | --- |
| Technische Universität München | `https://www.tum.de/news.rss` | `news` | `primary_evidence` |
| Max-Planck-Gesellschaft | `https://www.mpg.de/de/forschung.rss` | `news` | `primary_evidence` |
| Fraunhofer-Gesellschaft | `https://www.fraunhofer.de/de/rss/presse.rss` | `press_release` | `primary_evidence` |
| Karlsruher Institut für Technologie | `https://www.kit.edu/pi.rss` | `press_release` | `primary_evidence` |
| Charité — Universitätsmedizin Berlin | `https://www.charite.de/service/pressemitteilung/feed/pressefeed?type=102` | `press_release` | `primary_evidence` |

Max Planck's feed is named "Forschung", but its recent entries also contain
institutional announcements. It is therefore conservatively classified as
`news`, not `research_publication`.

## Reviewed channels not configured

The following channels were deliberately not added as runtime Feed candidates in
this pass.

### WZB publication RSS

`https://wzb.eu/en/rss_publications.xml` is technically valid, but the WZB
publication search is a bibliographic catalogue of publications by WZB
researchers and includes works published in external journals and other venues.
Treating every item as an ordinary WZB-originated article would blur source
identity and provenance.

### DIW general publications RSS

`https://www.diw.de/de/rss_publications.xml` is technically valid but combines
materially different publication types, including research output, comments,
interviews and newspaper/blog contributions. One feed-level confirmation role
would therefore be too coarse.

The dedicated DIW press-release feed is used instead.

### RWI feeds

`https://www.rwi-essen.de/rss-publication.feed` is a broad publication
catalogue. The separate `rss-standpunkte.feed` contains guest contributions
and interviews distributed through external media and repeatedly links to an
aggregate RWI media page. Neither is activated as a clean institutional
research feed.

### MERICS general RSS

`https://merics.org/en/rss` is technically valid but mixes reports, comments,
videos, briefs and external publications. It does not have one uniform
confirmation role or provenance semantics.

### General WordPress feeds

General feeds discovered for LibMod, Stiftung Marktwirtschaft, Das Progressive
Zentrum, Prometheus, REPUBLIK21 and ZOE contain mixed site content. They remain
unconfigured until a narrower, semantically stable channel is verified or
entry-level role routing is introduced.

### ZEW

The previously suspected
`https://www.zew.de/presse/pressemitteilungen/rss` route returned an HTML page,
not an RSS/Atom document, in direct parsing. No feed is configured from that
route.

### DLR and Forschungszentrum Jülich

Both organizations expose RSS-related service links, but this pass did not
produce a concrete general feed URL that passed direct RSS/Atom parsing for DLR,
and the Jülich short link `https://go.fzj.de/rss-feed` resolved to HTML rather
than a feed document. They remain unconfigured rather than being guessed.

## Ingestion compatibility finding

The DIW feeds use relative item URLs. FSC's FeedParser now resolves relative
feed, entry and enclosure links against the final fetched feed URL before
persistence. This keeps Article links canonical and usable by downstream
content retrieval.
