# United Kingdom editorial and primary-source feed activation review v1

Review date: 2026-09-29

## Scope

This review covers the approved United Kingdom national Print, Broadcast,
Digital and Primary Source catalogs. Regional/devolved broadcast remains
outside this activation pass.

Feed activation remains channel-specific. Catalog inclusion alone does not
materialize a Source. Existing print or broadcast newsrooms are extended by
Digital outlets instead of being duplicated as a second Source.

## Cross-media identity cleanup

The GB Digital catalog still contained thirteen print-origin brands as
`create_source` entries even though its identity policy already required
cross-media Sources to be extended rather than duplicated.

The following Digital entries now extend their canonical Print Sources:

- The Canary
- Morning Star
- Socialist Worker
- The Guardian
- New Statesman
- Financial Times
- The Economist
- The Times
- The Telegraph
- The Spectator
- The Critic
- Daily Mail
- Prospect

This is an identity correction only. The Digital entries carried no independent
classification assertions or metrics that would be lost by the change.

## Tier 1: activated editorial feeds

### Print / cross-media bases

- Socialist Worker — `https://socialistworker.co.uk/feed/`
- The Canary — `https://www.thecanary.co/feed/`
- The Guardian — `https://www.theguardian.com/uk/rss`
- New Statesman — `https://www.newstatesman.com/feed`
- Financial Times — `https://www.ft.com/rss/home`
- The Critic — `https://thecritic.co.uk/feed/`

All six feeds were validated as parseable current RSS feeds and use
`news -> editorial`. Their Digital catalog entries extend the same canonical
Source identity where applicable.

### Broadcast

- Channel 4 News — `https://www.channel4.com/news/feed`
- BBC News — `https://feeds.bbci.co.uk/news/rss.xml`
- Sky News — `https://feeds.skynews.com/feeds/rss/home.xml`
- GB News — `https://www.gbnews.com/feeds/feed.rss`

All four feeds were validated as RSS 2.0. The Channel 4 and GB News endpoints
were discovered from their public websites rather than guessed from generic
`/feed` paths.

### Digital-native / digital-first Sources

- Novara Media — `https://novaramedia.com/feed/`
- openDemocracy — `https://www.opendemocracy.net/en/feed/`
- Byline Times — `https://bylinetimes.com/feed/`
- UnHerd — `https://unherd.com/feed/`
- Spiked — `https://www.spiked-online.com/feed/`
- Full Fact — `https://fullfact.org/feed/`
- The Conversation UK — `https://theconversation.com/uk/articles.atom`

These endpoints were validated as current RSS or Atom feeds and use
`news -> editorial`.

## Tier 1: activated Primary Source feeds

Broad official agency/department feeds are classified in catalog review
metadata as `official_updates`, because they can contain news, guidance,
publications and other official material rather than only press releases.
`official_updates` maps to the existing runtime role `primary_evidence`; it
is not a persisted enum.

Activated official feeds:

- UK Government / Prime Minister's Office —
  `https://www.gov.uk/government/organisations/prime-ministers-office-10-downing-street.atom`
- Foreign, Commonwealth & Development Office —
  `https://www.gov.uk/government/organisations/foreign-commonwealth-development-office.atom`
- Home Office —
  `https://www.gov.uk/government/organisations/home-office.atom`
- Ministry of Defence —
  `https://www.gov.uk/government/organisations/ministry-of-defence.atom`
- HM Treasury —
  `https://www.gov.uk/government/organisations/hm-treasury.atom`
- UK Health Security Agency —
  `https://www.gov.uk/government/organisations/uk-health-security-agency.atom`
- Bank of England — `https://www.bankofengland.co.uk/rss/news`
- Financial Conduct Authority — `https://www.fca.org.uk/news/rss.xml`
- National Cyber Security Centre —
  `https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml`
- National Crime Agency —
  `https://www.nationalcrimeagency.gov.uk/news?format=feed&type=rss`
- Courts and Tribunals Judiciary — `https://www.judiciary.uk/feed/`

All were technically validated as parseable current official feeds.

## Reviewed but not activated

- Morning Star: the tested obvious `/feed/` endpoint did not expose a
  parseable feed.
- The Spectator: the tested `/feed/` endpoint returned no feed content in this
  review.
- Daily Mail: the tested `articles.rss` endpoint returned no usable content.
- PoliticsHome: the tested `/rss` endpoint did not parse as RSS/Atom.
- ITV News: no stable public feed was established in this pass.
- Office for National Statistics: tested obvious latest-release/article feed
  paths did not parse as a feed.
- Ofcom and Office for Budget Responsibility: tested obvious RSS/feed paths did
  not yield a parseable feed.
- UK Supreme Court: the tested guessed RSS news path did not yield a usable
  feed.
- Other cataloged Primary Sources remain catalog-only until a concrete stable
  official channel is reviewed.

## Runtime identity semantics

- `create_source` without a reviewed feed remains catalog-only.
- `extend_existing_source` never creates a duplicate Source.
- Digital cross-media outlets resolve to the canonical Print or Broadcast
  Source via `existing_source_key` and canonical name.
- Same-named outlets may coexist across media categories under ADR 0030.
- Runtime feeds not represented by these reviewed catalogs are preserved.
