# Switzerland organization feed activation review v1

Review date: 2026-09-28

## Scope

This review applies ADR 0027 to the Swiss `ACADEMIC`, `THINK_TANK`,
`COMPANY`, `NGO` and `INTEREST_GROUP` catalogs.

The same conservative rules used for Germany and Austria apply. Feed activation
is channel-specific; interest-bound research never becomes independent
confirmation merely because it looks analytical.

## Tier 1: activated

### ETH Zürich — Medienmitteilungen

- official Atom feed filtered to ETH media releases
- class: `press_release`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- direct parsing returned Atom 1.0 with current entries and no parser warnings.
- research announcements remain primary evidence for what ETH communicates;
  the press channel is not treated as a research-publication feed.

### Public Eye — News

- URL: `https://www.publiceye.ch/de/rssNews.xml`
- class: `news`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- Public Eye's official RSS service separates news, blog, events and
  publications; direct parsing of the news feed returned valid RSS 2.0.
- this avoids treating NGO investigations or reports as independent research.

### Schweizerische Flüchtlingshilfe (SFH) — Aktuelles

- URL: `https://www.fluechtlingshilfe.ch/rss.xml`
- class: `news`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- direct parsing returned current RSS 2.0 content.
- the feed mixes press releases with SFH news/stories, but the conservative
  `primary_evidence` role is valid for the organization's own communications.

### Schweizerischer Gewerbeverband (sgv) — Medienmitteilungen

- dedicated official media-release RSS endpoint
- class: `press_release`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- direct parsing returned RSS 2.0 with current policy and association releases.

## Tier 2: verified but initially disabled

### AlgorithmWatch CH — Aktuelles

- URL: `https://algorithmwatch.ch/de/rss`
- class: `news`
- role: `primary_evidence`
- status: inactive
- direct parsing is technically clean, but the broad channel contains event
  reports, commentary and policy updates and is lower priority than the
  dedicated channels above.

## Reviewed but not configured

### Avenir Suisse

The technically valid general feed is dominated by blog posts and mixes
analysis, commentary and other formats. It is not promoted to
`expert_analysis` merely because Avenir Suisse is a THINK_TANK. No narrower
publication RSS endpoint was verified in this pass.

### Public Eye publications

Public Eye exposes a separate publication RSS feed. It includes investigations,
reports, annual reports and other publication types. The news feed is used
initially to avoid parallel ingestion and unnecessary overlap.

### Swiss think tanks

Generic WordPress feeds found for the Liberales Institut and Denknetz are broad
site feeds. Other think-tank channels did not expose a sufficiently narrow,
verified feed endpoint in this pass.

### Swiss companies

No company feed discovered in this pass met both the stable-endpoint and
narrow-content requirements. No endpoint is guessed from a sitemap or service
page.

### Other NGOs and interest groups

General feeds remain inactive where a single content class is not stable enough
or a narrower official channel could not be verified.

## Multilingual handling

Swiss Sources remain multilingual at Source level. Feed activation does not add
a language dimension to the Feed model; Article language remains determined at
article/content level. A German-language feed therefore does not narrow the
Source identity or prevent later French, Italian or English channels from being
added to the same Source.
