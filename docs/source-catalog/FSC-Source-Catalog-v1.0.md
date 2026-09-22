# FSC Source Catalog v1.0

Status: working catalog for joint review. Catalog inclusion does **not** activate ingestion.

## Catalog rules

FSC keeps these dimensions separate:

1. **Country of origin** — country blocks are never merged. Germany, Austria and Switzerland are separate.
2. **Media category** — print, broadcast, digital-native, agency, primary source, organization, other.
3. **Publication form** — e.g. daily newspaper, weekly newspaper, magazine, periodical.
4. **Editorial orientation** — descriptive, provenance-backed metadata; never an FSC score.
5. **Radicality / external extremist classification** — separate from left/right orientation and always stored with classifier, source URL and reference date.
6. **Reach / circulation** — descriptive metadata with metric type, measurement body and reference period; never an inclusion criterion.
7. **Operational status** — catalog inclusion is separate from feed activation.

Target for political print segments: normally at least 3–5 newspaper/weekly-newspaper titles and 3–5 magazine/periodical titles where the active media landscape supports that. Real market gaps are recorded instead of relabelling publications to make the matrix symmetrical.

## Germany (DE)

### Print

All entries below are catalog candidates. None of them is authorized for production ingestion merely by appearing here.

#### A. Radical / system-oppositional left

| Title | Publication form | Notes |
| --- | --- | --- |
| junge Welt | daily newspaper | active print |
| Unsere Zeit | weekly newspaper | active print; publisher-reported circulation available |
| analyse & kritik | newspaper / periodical | active 2026 |
| Sozialistische Zeitung (SoZ) | newspaper / periodical | active print |
| Graswurzelrevolution | newspaper / periodical | active 2026; publisher-reported circulation available |
| Jacobin Deutschland | magazine | quarterly print |
| Antifaschistisches Infoblatt | magazine | active print |
| Rote Hilfe Zeitung | periodical | quarterly print |
| Marxistische Blätter | magazine | active 2026 |
| GegenStandpunkt | periodical | active print |

External classifications must be stored individually; the planning segment above is not itself a persisted FSC classification.

#### B. Left / centre-left / left-liberal

| Title | Publication form | Notes |
| --- | --- | --- |
| taz | daily newspaper + weekly edition | daily/e-paper and wochentaz metrics kept separate |
| Süddeutsche Zeitung | daily newspaper | national title |
| Frankfurter Rundschau | daily newspaper | national/regional title |
| DIE ZEIT | weekly newspaper | national weekly |
| der Freitag | weekly newspaper | national weekly |
| nd / Neues Deutschland | daily/weekly newspaper | active print |
| DER SPIEGEL | weekly magazine | current audited circulation available |
| Blätter für deutsche und internationale Politik | monthly magazine | current 2026 media data available |
| Publik-Forum | magazine | active print |
| stern | weekly magazine | orientation classification to be provenance-backed |
| iz3w | periodical | political/cultural periodical; classification to be provenance-backed |

#### C. Liberal / centre / economically liberal

| Title | Publication form | Notes |
| --- | --- | --- |
| Der Tagesspiegel | daily newspaper | current circulation/digital metrics available |
| Handelsblatt | business daily | current IVW metric available |
| Stuttgarter Zeitung | daily newspaper | regional/national relevance |
| Augsburger Allgemeine | daily newspaper | combination-vs-title metrics must remain distinct |
| Kölner Stadt-Anzeiger | daily newspaper | regional/national relevance |
| Rheinische Post | daily newspaper | regional/national relevance |
| WirtschaftsWoche | weekly magazine | current IVW metric available |
| Capital | magazine | business/economics |
| brand eins | magazine | current publisher/IVW metrics available |
| manager magazin | magazine | business/economics |
| MERKUR | periodical | cultural/political journal; exact classification provenance required |

#### D. Conservative / liberal-conservative

| Title | Publication form | Notes |
| --- | --- | --- |
| Frankfurter Allgemeine Zeitung | daily newspaper | national title |
| WELT | daily newspaper | current circulation/reach metrics available |
| BILD | daily newspaper / boulevard | boulevard is a format attribute, not an orientation |
| Münchner Merkur | daily newspaper | regional/national relevance |
| Die Tagespost | weekly newspaper | Catholic weekly; current 2026 media data available |
| FOCUS | weekly magazine | national news magazine |
| Cicero | monthly magazine | political magazine |
| Die Politische Meinung | periodical | Konrad-Adenauer-Stiftung; current 2026 issues |
| Schweizer Monat | **excluded from DE** | belongs to CH country block |
| Schweizerzeit | **excluded from DE** | belongs to CH country block |

The two excluded rows are retained only to make the country-boundary decision explicit and must not become DE source records.

#### E. Right / right-conservative / right-libertarian

| Title | Publication form | Notes |
| --- | --- | --- |
| Junge Freiheit | weekly newspaper | active 2026; regular circulation distinct from special-edition print runs |
| Preußische Allgemeine Zeitung | weekly newspaper | active 2026 |
| Epoch Times Deutschland | weekly newspaper | active print/e-paper; external classification provenance required |
| Tichys Einblick | monthly magazine | active 2026 |
| CATO | bimonthly magazine | 2026 publisher-reported print run available |
| eigentümlich frei | magazine | active; current 2026 media rates |
| TUMULT | periodical | active publishing program; cadence to be represented precisely |

#### F. Radical right / externally classified extreme-right spectrum

| Title | Publication form | Notes |
| --- | --- | --- |
| Zündstoff | quarterly newspaper / information paper | active 2026 |
| Stimme Deutschlands | irregular party publication | publication form/current activity requires final current-source verification |
| COMPACT | monthly magazine | active print 2026; external classification provenance required |
| Sezession | bimonthly periodical | six 2026 issues |
| ZUERST! | magazine | active print 2026 |
| AUFGEWACHT – DIE DEUTSCHE STIMME | monthly magazine | magazine since 2025 merger; not a newspaper |
| N.S. Heute | bimonthly magazine | active 2026; official external classification provenance available |
| Volk in Bewegung – Der Reichsbote | periodical / magazine | active 2026 |
| Unabhängige Nachrichten | monthly periodical | publication/category provenance required before acceptance |

This segment is genuinely magazine-heavy in the current German print market. FSC records that asymmetry rather than reclassifying magazines as newspapers merely to reach a numerical quota.

## Reach and circulation model

Metrics are historical observations, not properties overwritten on the source.

Required fields are represented by the provenance-aware `SourceMetric` model:

- metric kind (sold circulation, distributed circulation, print run, print readers, digital unique users, visits, page impressions, paid digital subscriptions, subscribers)
- value and unit
- scope
- reference period and optional start/end
- measurement body
- provenance URL
- audited flag
- retrieval timestamp
- optional outlet link and notes

Rules:

- IVW/audited figures and publisher-reported figures are never treated as equivalent.
- Special-edition print runs are not regular sold circulation.
- Print circulation, readers, digital unique users, visits and page impressions remain separate metrics.
- Missing current metrics stay NULL; stale figures are not copied forward merely to fill a field.
- Reach never decides whether a source is eligible for the catalog.

## Classification model

`SourceClassification` stores assertions from identified classifiers rather than an FSC-generated ideology score.

Required provenance:

- dimension
- reported classification value
- optional detail
- classifier type and name
- source URL
- reference date
- optional validity range
- retrieval timestamp
- notes

Self-description, media-database classification, academic classification, public-authority classification and court findings remain distinguishable.

## Country blocks after DE

The same taxonomy is applied independently to:

1. Austria (AT)
2. Switzerland (CH)
3. United Kingdom (GB)
4. United States (US)
5. Canada (CA)
6. France (FR)
7. Italy (IT)
8. Spain (ES)
9. Poland (PL)
10. Benelux and Nordic countries as separate country records
11. further internationally relevant countries

Foreign-language media are not deferred. FSC v1.0 cross-language story matching is part of the current product scope.

## Activation rule

A catalog entry may only receive active production feeds after joint source review. Building the catalog, metadata model, provenance records and technical feed validation does not itself authorize activation.
