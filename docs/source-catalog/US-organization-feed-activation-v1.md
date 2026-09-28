# United States organization feed activation review v1

Review date: 2026-09-28

## Scope

This review applies ADR 0027 to the United States `ACADEMIC`,
`THINK_TANK`, `COMPANY`, `NGO` and `INTEREST_GROUP` catalogs.

The same conservative rules used for Germany, Austria, Switzerland and the
United Kingdom continue to apply. Feed activation is channel-specific.
Analytical form does not by itself establish independence, and research from
`COMPANY`, `NGO` or `INTEREST_GROUP` Sources remains interest-bound.

## Tier 1: activated

### Massachusetts Institute of Technology (MIT) — Research News

- URL: `https://news.mit.edu/rss/research`
- class: `news`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- MIT News documents separate main feeds for Latest News, Research News and
  Campus News.
- the Research News channel contains institutional reporting about MIT
  research rather than the underlying papers themselves.
- it is therefore deliberately classified as `news`, not
  `research_publication`, and does not create independent confirmation.

### Apple Inc. — Apple Newsroom

- URL: `https://www.apple.com/newsroom/rss-feed.rss`
- class: `news`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- Apple publishes an official Newsroom RSS feed.
- the channel contains press releases, updates and other company newsroom
  material, so `news` is the conservative common class.

### NVIDIA Corporation — Press Releases

- URL: `https://nvidianews.nvidia.com/cats/press_release.xml`
- class: `press_release`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- NVIDIA's official Newsroom RSS directory exposes a dedicated Press Releases
  feed separate from blogs and topical feeds.
- the dedicated endpoint is preferred over the broader all-news channel.

## Tier 2: verified but initially disabled

### Harvard University — Harvard Gazette

- URL: `https://news.harvard.edu/gazette/feed`
- class: `news`
- role: `primary_evidence`
- priority: 2
- interval: 120 minutes
- Harvard Gazette documents an all-stories RSS feed and topic-specific feeds.
- the all-stories channel mixes research coverage, campus news and other
  institutional stories.
- it is retained as a verified candidate but initially disabled because its
  breadth makes it less targeted than MIT Research News.

## Reviewed but not configured

### US think tanks

Several major US think tanks expose broad site feeds, newsletters or
publication pages, but this pass did not verify a narrow, stable RSS/Atom
channel whose contents are consistently analytical enough to justify
`research_publication -> expert_analysis` without entry-level classification.

The Center for American Progress publicly documents a general RSS feed, but the
corresponding content stream spans reports, articles, statements and other
formats. It remains unconfigured instead of forcing one confirmation role onto
materially different content.

### NGOs

The ACLU exposes a current press-release archive, and EFF historically
documents dedicated RSS feeds, but this pass did not verify a current stable
RSS/Atom endpoint with sufficiently clear runtime behavior for the selected
national NGO Sources. No NGO feed is guessed from page structure.

### Interest groups

No reviewed national interest-group endpoint in this pass met both the
stable-feed and coherent-content requirements. In particular, the National
Association of Realtors explicitly states that it is not currently offering an
RSS feed subscription service.

## Source identity and role semantics

The Source remains the institutional unit from the existing catalog. Feeds do
not create separate Sources for brands, publication channels or subunits.

`ACADEMIC` and `THINK_TANK` Sources may use `expert_analysis` only for a
concrete consistently analytical channel. Institutional news about research is
not equivalent to the research publication itself.

`COMPANY`, `NGO` and `INTEREST_GROUP` research remains interest-bound and
does not become independent confirmation merely because the content is
analytical.
