# DE editorial and primary-source feed activation review v1

Review date: 2026-09-29

## Scope

This review activates a conservative first ingestion set from the approved DE
print, digital, national broadcast and primary-source catalogs.

The catalog membership remains broader than runtime ingestion. Only concrete,
official and technically verified feeds are configured. Entries without a
reviewed feed stay catalog-only.

The A-F planning groups remain research planning metadata only. Feed activation
does not persist or infer a political classification.

## Runtime role semantics

Editorial NEWS Sources:

- `news -> editorial`

Primary Sources:

- `press_release -> primary_evidence`
- `official_data -> primary_evidence`

This preserves the existing rule that primary evidence can substantiate a fact
but is not independent editorial confirmation.

## Tier 1 editorial feeds

### Print / cross-media newsroom Sources

- taz — `https://taz.de/rss.xml`
- DER SPIEGEL — `https://www.spiegel.de/schlagzeilen/index.rss`
- WELT — `https://www.welt.de/feeds/latest.rss`
- Junge Freiheit — `https://jungefreiheit.de/feed/`
- Tichys Einblick — `https://www.tichyseinblick.de/feed/`

All five endpoints were fetched and parsed successfully as RSS feeds during the
review. The configured feed belongs to the canonical Source, not to a separate
digital Source.

### Digital-native Sources

- NachDenkSeiten — `https://www.nachdenkseiten.de/?feed=rss2`
- Apollo News — `https://apollo-news.net/feed/`
- netzpolitik.org — `https://netzpolitik.org/feed/`

netzpolitik.org remains politically unclassified in the source catalog. Feed
activation does not move it into an A-F planning group.

### National broadcast Sources

Existing production feeds are adopted into catalog management without changing
their Source UUIDs, Feed UUIDs or legacy slugs:

- Deutschlandradio — Deutschlandfunk Nachrichten:
  `https://www.deutschlandfunk.de/nachrichten-100.rss`
- ARD-aktuell — Alle Meldungen:
  `https://www.tagesschau.de/infoservices/alle-meldungen-100~rss2.xml`
- ZDF — Nachrichten:
  `https://www.zdf.de/rss/zdf/nachrichten`

The feed default role becomes explicit `editorial`. Existing Article roles
remain non-retroactive under ADR 0027.

## Tier 1 primary-source feeds

### Deutscher Bundestag

- Pressemitteilungen:
  `https://www.bundestag.de/static/appdata/includes/rss/pressemitteilungen.rss`
- class: `press_release`
- role: `primary_evidence`

The Bundestag officially documents multiple RSS services, including press
releases, parliamentary short notices, documents and plenary protocols. The
press-release stream is used as the initial narrow runtime channel.

### Bundesregierung / Bundespresseamt

- Pressemitteilungen:
  `https://www.bundesregierung.de/service/rss/breg-de/1151244/feed.xml`
- class: `press_release`
- role: `primary_evidence`

The official RSS page separates press releases from the broader mixed
"Bundesregierung kompakt" stream. The narrower press-release feed is selected.

### Statistisches Bundesamt (Destatis)

- Aktuelle Meldungen:
  `https://www.destatis.de/SiteGlobals/Functions/RSSFeed/DE/RSSNewsfeed/Aktuell.xml`
- class: `official_data`
- role: `primary_evidence`

The current feed contains Destatis statistical releases and is treated as
official evidence rather than independent editorial confirmation.

### Deutsche Bundesbank

- Pressenotizen:
  `https://www.bundesbank.de/service/rss/de/633286/feed.rss`
- class: `press_release`
- role: `primary_evidence`

The Bundesbank publishes a dedicated RSS directory. The narrower Pressenotizen
feed is selected instead of the general all-site feed.

## Reviewed but not activated in this pass

Potential feed links for some other catalog Sources were either absent, mixed,
or did not parse as stable RSS/Atom endpoints during verification. In
particular, no feed is configured merely because a URL contains "rss", "feed"
or "atom".

Examples deliberately not activated in this pass include candidate endpoints
for Achgut and Multipolar that returned non-feed content to the parser.

## Deutsche Welle runtime exception

Deutsche Welle remains an active, healthy runtime Source with
`coverage_scope=GLOBAL` and its existing German-language feed.

It is deliberately not managed by the DE national broadcast catalog. The
approved national catalog already defers Deutsche Welle because German linear
TV distribution is not part of the current DE-national scope.

No international broadcast catalog is created in this pass. Deutsche Welle is
therefore retained as an explicit healthy global legacy/runtime exception until
a future international/digital catalog review decides its catalog ownership.

## Materialization policy

The existing ADR 0028 reconciliation command is used.

- dry-run remains the default;
- only entries with reviewed feeds materialize;
- runtime feeds outside the selected catalogs are preserved;
- no destructive feed removal occurs;
- `feed_class` and `activation_tier` remain catalog-only metadata;
- `--apply` remains transactional.
