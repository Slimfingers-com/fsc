# Austria editorial and primary-source feed activation review v1

Review date: 2026-09-29

## Scope

This review covers the approved Austria national Print, Broadcast, Digital and
Primary Source catalogs. Regional broadcast remains a separate catalog and is
not activated by this review.

Only stable, directly fetchable RSS/Atom endpoints that were technically
validated against the existing feed parser are configured. Catalog inclusion
alone does not imply runtime ingestion.

## Tier 1: Print

### Der Standard

- URL: `https://www.derstandard.at/rss`
- class: `news`
- role: `editorial`
- interval: 30 minutes
- valid RSS 2.0 feed; 156 entries observed during review.

### Falter

- URL: `https://www.falter.at/rss`
- class: `news`
- role: `editorial`
- interval: 30 minutes
- valid RSS 2.0 feed; 100 entries observed during review.

### Die Presse

- URL: `https://www.diepresse.com/rss`
- class: `news`
- role: `editorial`
- interval: 30 minutes
- valid RSS 2.0 feed; 77 entries observed during review.

### Kurier

- URL: `https://kurier.at/xml/rss`
- class: `news`
- role: `editorial`
- interval: 30 minutes
- valid RSS 2.0 feed.

## Tier 1: Broadcast

### ORF Information

- URL: `https://rss.orf.at/news.xml`
- class: `news`
- role: `editorial`
- interval: 15 minutes
- ORF exposes this feed from its public news site; it parsed cleanly as RSS.

### AUF1

- URL: `https://auf1.tv/feed/`
- class: `news`
- role: `editorial`
- interval: 30 minutes
- valid RSS 2.0 feed.
- the Feed is attached to the canonical AUF1 Source from the broadcast catalog;
  the digital catalog remains an Outlet extension of that Source.

## Tier 1: Digital

### MOMENT

- URL: `https://www.moment.at/feed`
- class: `news`
- role: `editorial`
- interval: 30 minutes
- valid RSS 2.0 feed.

### eXXpress

- URL: `https://exxpress.at/feed/`
- class: `news`
- role: `editorial`
- interval: 30 minutes
- valid RSS 2.0 feed.

### Unzensuriert

- URL: `https://unzensuriert.at/feed/`
- class: `news`
- role: `editorial`
- interval: 30 minutes
- valid RSS 2.0 feed.

### Report24

- URL: `https://report24.news/feed/`
- class: `news`
- role: `editorial`
- interval: 30 minutes
- valid RSS 2.0 feed.

### ZackZack

- URL: `https://zackzack.at/feed/`
- class: `news`
- role: `editorial`
- interval: 30 minutes
- valid RSS 2.0 feed.

## Reviewed but not activated

### profil

The official site exposes `https://www.profil.at/xml/rss`, and the endpoint is
technically valid RSS. During review the aggregate feed included APA-OTS /
press-release material. It is therefore not assigned one uniform editorial
confirmation role in this pass.

### Primary Sources

No Austria Primary Source Feed is activated in this pass.

The Austrian Parliament officially supports RSS exports for many filtered
searches, including legislative initiatives, resolutions, plenary material and
other parliamentary objects. Those feeds are generated from query/export
configuration rather than one stable reviewed GET endpoint selected for FSC.

Statistik Austria currently promotes publication calendars and mail
subscriptions for new data releases. OeNB currently documents newsletter
subscriptions for press releases and other updates. No stable simple RSS/Atom
endpoint was verified for these catalog Sources in this review.

The absence of an activated Feed does not remove these Sources from the Primary
Source catalog.

## Cross-media identity

Where a Print or Broadcast Source also appears in the Digital catalog,
`extend_existing_source` remains authoritative. A digital website or TV/radio
channel adds an Outlet to the existing Source and does not create an independent
Source.

This applies in particular to Der Standard, Falter, Die Presse, Kurier, ORF
Information and AUF1.

## Regional broadcast

`at_regional_broadcast_v1.json` remains unreviewed for feed activation. No
regional Source is used to fill national-feed coverage gaps.
