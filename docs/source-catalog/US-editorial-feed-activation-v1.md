# United States editorial and primary-source feed activation review v1

Review date: 2026-09-29

## Scope

This review covers the approved United States national Print, Broadcast, Digital
and Primary Source catalogs. Regional broadcast remains outside this activation
pass.

Feed activation is channel-specific. Catalog inclusion alone does not
materialize a Source. Cross-media entries continue to reuse the same canonical
Source identity and may add reviewed Outlets without duplicating Sources.

Only currently parseable, content-relevant feeds were selected. A technically
reachable endpoint was not accepted when it was empty, stale, or did not behave
as a coherent editorial or official-content channel.

## Tier 1: activated

### Print / publication-origin editorial Sources

- Workers World — `https://www.workers.org/feed/`
- Socialist Alternative — `https://www.socialistalternative.org/feed/`
- Jacobin — `https://jacobin.com/feed`
- Monthly Review — `https://monthlyreview.org/feed/`
- The New York Times — `https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml`
- The Washington Post — `https://feeds.washingtonpost.com/rss/politics`
- Los Angeles Times — `https://www.latimes.com/world-nation/rss2.0.xml`
- Mother Jones — `https://www.motherjones.com/feed/`
- The New Republic — `https://newrepublic.com/rss.xml`
- Dissent — `https://www.dissentmagazine.org/feed/`
- Reason — `https://reason.com/feed/`
- Newsweek — `https://www.newsweek.com/rss`
- National Review — `https://www.nationalreview.com/feed/`
- Washington Examiner — `https://www.washingtonexaminer.com/feed`
- New York Post — `https://nypost.com/feed/`
- La Opinión — `https://laopinion.com/feed/`

All are configured as `news -> editorial` with a 30-minute interval.

### Broadcast editorial Sources

- Democracy Now! — `https://www.democracynow.org/democracynow.rss`
- PBS NewsHour — `https://www.pbs.org/newshour/feeds/rss/headlines`
- NPR — `https://feeds.npr.org/1001/rss.xml`
- ABC News — `https://abcnews.go.com/abcnews/topstories`
- CBS News — `https://www.cbsnews.com/latest/rss/main`
- NBC News — `https://feeds.nbcnews.com/nbcnews/public/news`
- Fox News — `https://moxie.foxnews.com/google-publisher/latest.xml`

These are configured as `news -> editorial` with a 15-minute interval.

Their Digital catalog extensions remain feedless and extend the same canonical
Source identity.

### Digital-native editorial Sources

- Truthout — `https://truthout.org/feed/`
- Vox — `https://www.vox.com/rss/index.xml`
- The Intercept — `https://theintercept.com/feed/?rss`
- The Dispatch — `https://thedispatch.com/feed/`
- The Bulwark — `https://www.thebulwark.com/feed`
- Breitbart — `https://www.breitbart.com/feed/`
- The Gateway Pundit — `https://www.thegatewaypundit.com/feed/`
- ProPublica — `https://www.propublica.org/feeds/propublica/main`
- The Hill — `https://thehill.com/feed/`

All are configured as `news -> editorial` with a 30-minute interval.

### Primary Sources

- U.S. Census Bureau — `https://www.census.gov/newsroom/press-releases.xml`
  - class: `press_release`
- Bureau of Economic Analysis — `https://apps.bea.gov/rss/rss.xml`
  - class: `official_data`
- Federal Reserve Board — `https://www.federalreserve.gov/feeds/press_all.xml`
  - class: `press_release`
- Centers for Disease Control and Prevention —
  `https://tools.cdc.gov/api/v2/resources/media/132608.rss`
  - class: `press_release`
- U.S. Securities and Exchange Commission —
  `https://www.sec.gov/news/pressreleases.rss`
  - class: `press_release`
- Federal Trade Commission —
  `https://www.ftc.gov/feeds/press-release.xml`
  - class: `press_release`
- Federal Bureau of Investigation —
  `https://www.fbi.gov/feeds/fbi-in-the-news/atom.xml`
  - class: `press_release`

All Primary Source feeds use `primary_evidence` and a 60-minute interval.

## Tier 2: reviewed but production-inactive

The following reviewed endpoints remain catalogued but are inactive in runtime
because they returned HTTP 403 from the Hetzner production host on 2026-09-30,
including with a browser-style User-Agent:

- The Atlantic — `https://www.theatlantic.com/feed/all/`
- The Washington Times — `https://www.washingtontimes.com/rss/headlines/news/`
- The 19th — `https://19thnews.org/feed/`
- Cybersecurity and Infrastructure Security Agency —
  `https://www.cisa.gov/news.xml`

They remain Tier 2 so the reviewed endpoint identity is preserved without
causing repeated production fetch failures. No replacement URL is guessed.

## Reviewed but not activated

- CNN: the classic top-stories RSS endpoint remains parseable but the sampled
  leading item was from 2023 while the review date is 2026. It is therefore
  treated as stale and not activated.
- The Nation: the tested feed parsed as RSS but contained no entries.
- USA Today, Current Affairs, Common Dreams, POLITICO, The Federalist,
  American Free Press and The Epoch Times: tested obvious public feed endpoints
  did not produce a usable parseable feed.
- In These Times: the tested RSS endpoint returned entries but remained in a
  parser error state; it is not activated in this pass.
- Newsmax: the tested RSS endpoint returned no content.
- White House, Department of State, DHS, Treasury, Commerce, Labor, BLS, FCC,
  FERC and the tested Senate caucus feeds: the obvious official endpoints
  tested in this pass did not yield a stable parseable feed.
- Department of Defense: the tested RSS endpoint was syntactically valid but
  empty and is not activated.

No replacement URL is guessed for any rejected endpoint.

## Runtime identity semantics

- `create_source` entries without reviewed feeds remain catalog-only.
- `extend_existing_source` entries never create duplicate Sources.
- Cross-media Outlets are identified by Source, normalized outlet name and media
  category, so equal brand names can coexist across Print, Broadcast and Digital.
- Extension feeds, when present, attach to the same canonical Source.
- Missing extension bases fail closed where a reviewed Feed depends on them.
- Runtime feeds not represented in the reviewed catalog are preserved.
