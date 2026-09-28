# Germany NGO and interest-group feed activation review v1

Review date: 2026-09-28

## Scope

This review covers the first feed-activation pass for the existing German
`NGO` and `INTEREST_GROUP` source catalogs.

The activation rules follow ADR 0027:

- activate concrete official content channels, not whole Sources blindly;
- treat feed class as catalog/review metadata only;
- persist only runtime Feed fields, including `default_confirmation_role`;
- keep interest-bound research conservative: research-shaped material does not
  become independent confirmation merely because it is analytical;
- leave mixed, provenance-ambiguous or weakly scoped general feeds inactive
  unless one conservative role is clearly valid for the whole channel.

For both `NGO` and `INTEREST_GROUP`, the reviewed mapping is:

| Feed class | Default role |
| --- | --- |
| `research_publication` | `advocacy` |
| `official_data` | `primary_evidence` |
| `press_release` | `primary_evidence` |
| `news` | `primary_evidence` |
| `position_statement` | `advocacy` |
| `signal` | `signal` |

## Tier 1: activated

### PRO ASYL — News

- URL: `https://www.proasyl.de/news/feed/`
- feed class: `news`
- default confirmation role: `primary_evidence`
- scheduler priority: 1
- fetch interval: 60 minutes
- status: active
- verification: direct FSC fetching and parsing returned RSS 2.0 with current
  entries and no parser warnings.
- rationale: migration and asylum policy are high-relevance FSC topics. The
  channel is primary evidence for PRO ASYL's own statements, actions and
  reporting, not independent confirmation.

### Mehr Demokratie — Pressemitteilungen

- URL: `https://www.mehr-demokratie.de/rss-press.xml`
- feed class: `press_release`
- default confirmation role: `primary_evidence`
- scheduler priority: 1
- fetch interval: 60 minutes
- status: active
- verification: the official site exposes separate news and press RSS feeds;
  direct parsing of the press feed returned current RSS 2.0 entries without
  parser warnings.
- rationale: the dedicated press channel is cleaner than the broader news feed
  and is relevant to election, participation and institutional-reform coverage.

### Deutscher Gewerkschaftsbund (DGB) — Pressemitteilungen

- URL: `https://www.dgb.de/pressemitteilungen-rss-feed.xml`
- feed class: `press_release`
- default confirmation role: `primary_evidence`
- scheduler priority: 1
- fetch interval: 60 minutes
- status: active
- verification: the official DGB site exposes separate RSS channels for news,
  press releases and tariff updates; direct parsing of the press feed returned
  current RSS 2.0 entries without parser warnings.
- rationale: the dedicated press feed is highly relevant for labor, social,
  wage and economic-policy coverage while keeping DGB-originated statements
  clearly primary rather than independent evidence.

### Verbraucherzentrale Bundesverband (vzbv) — Pressemitteilungen

- URL: `https://www.vzbv.de/presse/pressemitteilungen/rss.xml`
- feed class: `press_release`
- default confirmation role: `primary_evidence`
- scheduler priority: 1
- fetch interval: 60 minutes
- status: active
- verification: the official vzbv RSS service lists a dedicated press-release
  feed; direct FSC parsing returned current RSS 2.0 entries without warnings.
- rationale: high relevance for consumer protection, digital policy,
  regulation and litigation-related claims.

## Reviewed but not configured

### NABU

`https://www.nabu.de/rssfeed.php` is technically valid RSS, but the channel
mixes current news, campaigns, partner material, promotional content and service
items. It is not activated merely because it parses cleanly.

### LobbyControl

`https://www.lobbycontrol.de/feed` is technically valid but mixes formal
press releases with commentary, campaign material and other editorial formats.
A single persisted feed role would be too coarse for the first activation pass.

### Welthungerhilfe

`https://www.welthungerhilfe.de/rss-whh.xml` is valid RSS but mixes press
releases, humanitarian operational updates, petitions and campaign material.
No single clean content class is assigned.

### Political and operational foundations

The Heinrich-Böll-Stiftung, Rosa-Luxemburg-Stiftung and
Desiderius-Erasmus-Stiftung expose technically parseable feeds. The reviewed
general/publication feeds combine analytical publications, institutional news,
events, commentary and, in some cases, externally hosted material. They remain
inactive rather than being treated as independent research feeds.

### DGB general news and tariff feeds

The DGB news feed is broader and more position-oriented than the dedicated
press channel. The tariff feed also reports updates originating from member
unions and sectoral negotiations, so activating it directly under the DGB
Source would require additional provenance review.

### dbb, BDA and Haus & Grund

Their technically valid general feeds are dominated by institutional positions
but are not narrow enough to guarantee a stable `position_statement` class for
every item. They remain unconfigured.

### BDI

The official BDI press service is highly relevant and current, but this review
did not identify a stable RSS/Atom endpoint that passed direct ingestion.
No URL is guessed.

### vzbv general publication feed

The publication feed overlaps substantially with press releases, judgments and
other content classes. The dedicated press-release feed is used instead.

## Runtime consequence

The four Tier-1 channels override the SourceType fallback of `advocacy` with
`primary_evidence` only because they are official news/press channels and are
primary evidence for what the originating organization says or does.

They do not create independent confirmation. Research or analysis from an
interest-bound NGO or membership body remains `advocacy` by default unless an
Article receives an explicit reviewed role.
