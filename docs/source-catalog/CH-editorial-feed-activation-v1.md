# Switzerland editorial and primary-source feed activation review v1

Review date: 2026-09-29

## Scope

This review covers the approved Swiss national Print, Broadcast, Digital and
Primary Source catalogs. Regional broadcast remains outside this activation
pass.

Feed activation remains channel-specific. Catalog inclusion alone does not
materialize a Source. Cross-media entries use the existing Source identity and
may add reviewed outlets without creating duplicate Sources.

Switzerland's multilingual catalog remains intact. A language-region Source is
not activated merely to satisfy language coverage when no stable parseable feed
has been verified.

## Tier 1: activated

### Print / cross-media editorial Sources

- solidaritéS
  - `https://solidarites.ch/feed/`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - validated as RSS 2.0 with current editorial items.
- Voix Populaire
  - `https://voixpopulaire.ch/feed/`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - validated as RSS 2.0 with current editorial items.
- WOZ – Die Wochenzeitung
  - `https://www.woz.ch/t/startseite/feed`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - validated as RSS 2.0; the common `/rss`, `/rss.xml` and `/feed` paths
    did not expose the usable feed.
- Le Courrier
  - `https://lecourrier.ch/feed/`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - validated as RSS 2.0 with current editorial items.
- Neue Zürcher Zeitung
  - `https://www.nzz.ch/recent.rss`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - validated as RSS 2.0.
- Schweizerzeit
  - `https://schweizerzeit.ch/feed/`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - validated as RSS 2.0.

Where these Sources also appear in the Digital catalog, the Digital entries
extend the same canonical Source rather than creating duplicates.

### Broadcast

- SRF
  - `https://www.srf.ch/news/bnf/rss/1646`
  - class: `news`
  - role: `editorial`
  - 30 minutes
  - validated as RSS 2.0.
  - feed title is the general SRF News stream ("Aktuelle News aus der Schweiz
    und weltweit – SRF"); this was preferred over the broader "Das Neueste"
    stream.

### Digital-native Sources

- Infosperber — `https://www.infosperber.ch/feed/`
- Inside Paradeplatz — `https://insideparadeplatz.ch/feed/`

Both endpoints were validated as parseable RSS 2.0 feeds with current editorial
items and use `news -> editorial`.

### Primary Source

- Schweizerische Nationalbank (SNB)
  - `https://www.snb.ch/public/rss/de/pressrel`
  - class: `press_release`
  - role: `primary_evidence`
  - 60 minutes
  - official SNB RSS channel for general media releases; validated as RSS 2.0
    with current SNB releases.

## Reviewed but not activated

- RTS, RSI and RTR: obvious public RSS/feed paths tested in this review did not
  return a parseable RSS/Atom feed. No guessed or fragile endpoint is activated
  solely to fill French, Italian or Romansh coverage.
- Corriere del Ticino: tested `/rss` and `/rss.xml` endpoints did not parse
  as a feed.
- Le Temps, Blick, Watson, Nau.ch, TicinOnline, Die Weltwoche and Nebelspalter:
  the obvious public RSS/feed paths tested did not return a parseable feed.
- Kla.TV and Schweizer Demokrat: tested obvious feed paths did not return a
  parseable feed.
- Antithèse & Bon pour la tête: a technically parseable endpoint was found, but
  it contained only a single test/event item and was not accepted as a coherent
  editorial-news feed.
- Other Primary Sources: no stable official feed was selected in this pass.
  They remain catalog-only until a concrete official channel is reviewed.

## Runtime identity semantics

- `create_source` entries without reviewed feeds remain catalog-only.
- `extend_existing_source` entries never create a duplicate Source.
- If the canonical Source already exists, reviewed cross-media outlets may be
  reconciled onto it even when the extension has no separate feed.
- If an extension itself has a configured feed, its base Source must already
  exist; otherwise reconciliation fails closed.
- Missing feedless extension bases are staged/skipped rather than forcing
  catalog-only Sources into runtime.
