# Germany company feed activation review v1

Review date: 2026-09-28

## Scope

This review covers the first feed-activation pass for the existing German
`COMPANY` source catalog.

The activation rules follow ADR 0027:

- activate concrete official content channels, not whole Sources blindly;
- use `feed_class` as catalog/review metadata only;
- persist only the runtime Feed fields, including
  `default_confirmation_role`;
- do not let analytical form create independent confirmation for an
  interest-bound institutional Source;
- keep mixed, technically weak or provenance-ambiguous channels inactive until
  a narrower stable channel is verified.

For `COMPANY`, the reviewed feed-role mapping is:

| Feed class | Default role |
| --- | --- |
| `research_publication` | `advocacy` |
| `official_data` | `primary_evidence` |
| `press_release` | `primary_evidence` |
| `news` | `primary_evidence` |
| `position_statement` | `advocacy` |
| `signal` | `signal` |

Corporate research can be valuable evidence and analysis, but it does not become
an independent confirmation merely because it is research-shaped. Article-level
review remains authoritative.

## Tier 1: activated

### Volkswagen AG (Volkswagen Group) — Pressemitteilungen

- URL: `https://www.volkswagen-group.com/de/feeds/pressemitteilungen`
- feed class: `press_release`
- default confirmation role: `primary_evidence`
- scheduler priority: 1
- fetch interval: 60 minutes
- status: active
- verification: the official Volkswagen Group press-release service exposes a
  German RSS 2.0 feed; direct parsing returned 100 current entries without a
  feedparser error.
- rationale: high relevance to German industry, employment, mobility,
  investment and industrial-policy coverage. The feed is primary evidence for
  Volkswagen statements and actions, not independent confirmation.

### Deutsche Lufthansa AG (Lufthansa Group) — Newsroom

- URL: `https://newsroom.lufthansagroup.com/feed/`
- feed class: `news`
- default confirmation role: `primary_evidence`
- scheduler priority: 1
- fetch interval: 60 minutes
- status: active
- verification: the official Lufthansa Group newsroom explicitly links its RSS
  feed; direct parsing returned a German RSS 2.0 feed with current newsroom
  entries.
- rationale: high relevance for transport, aviation, infrastructure,
  sustainability, labor and corporate-policy coverage. The newsroom contains a
  broader mix than formal press releases, so it is classified conservatively as
  `news`.

### Deutsche Bank AG — News and media

- URL: `https://www.db.com/api/sitemap/www.db.com/rss/3?newscount=30`
- feed class: `news`
- default confirmation role: `primary_evidence`
- scheduler priority: 1
- fetch interval: 60 minutes
- status: active
- verification: Deutsche Bank's official media page links this RSS endpoint;
  direct parsing returned RSS 2.0 with 30 current entries.
- rationale: high relevance for finance, capital markets, economy and
  regulatory-policy coverage. The feed mixes media releases and other
  Deutsche-Bank-authored newsroom material, so it is deliberately not treated
  as `research_publication` or independent analysis.

## Tier 2: verified but initially disabled

### Fresenius SE & Co. KGaA — Media news

- URL: `https://www.fresenius.com/news/rss?type=media`
- feed class: `press_release`
- default confirmation role: `primary_evidence`
- scheduler priority: 2
- fetch interval: 120 minutes
- status: inactive
- verification: Fresenius' official RSS service lists a dedicated media feed.
  The endpoint parses as RSS 2.0 and returns current media entries.
- reason for Tier 2: the server currently labels the RSS response as
  `text/html`, feedparser reports a bozo warning, and several item URLs contain
  redundant path slashes. The content is relevant but does not justify adding
  avoidable ingestion noise in the first activation set.

## Reviewed but not configured

### Bayer AG

Bayer's official RSS page states that it provides a Corporate News feed for
internationally relevant Bayer Group press releases. During this review the
runtime probe could not recover a stable directly parseable Corporate News feed
URL from the current page delivery. No URL is guessed into the catalog.

### Siemens AG

The current official Siemens press/news pages provide current press releases,
but this review did not identify a stable official RSS/Atom endpoint that passed
direct parsing. No feed is configured.

### BASF SE

BASF maintains current official news-release pages, but no stable RSS/Atom
endpoint was verified in this pass. No feed is configured.

### RWE AG

RWE maintains an official press and news service. This pass did not identify a
stable RSS/Atom endpoint suitable for direct FSC ingestion.

### Deutsche Telekom AG

The official corporate site exposes current newsroom content, but no clean
RSS/Atom channel was verified in this pass.

### Allianz SE and other financial companies

Research and newsroom material may be highly relevant. Any future corporate
research channel remains `advocacy` by default under ADR 0027 unless an
Article receives an explicit reviewed role. No research feed is activated merely
because its output is analytical.

## Runtime consequence

The activated Tier-1 feeds deliberately override the `COMPANY` SourceType
fallback of `advocacy` with `primary_evidence` because press/news items are
primary evidence for the company's own statements, actions and reported data.

They do not create independent confirmation. Corporate analytical publications
remain `advocacy` by default.
