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

## Austria (AT)

### Print

Austria is a separate country block. German, Swiss and Austrian titles are never merged into a single national catalog merely because they share a language.

All entries below are catalog candidates only; no feed is activated by catalog inclusion.

#### A. Radical / system-oppositional left

| Title | Publication form | Notes |
| --- | --- | --- |
| Der Funke | newspaper / periodical | active 2026; self-described revolutionary-communist workers' newspaper |
| Die Rote Fahne | newspaper / periodical | active print 2026 |
| Offensiv | newspaper / periodical | active 2026; irregular publication |
| In Verteidigung des Marxismus | magazine | active print 2026 |
| Volksstimme | periodical | active 2026; self-description "Zwischenrufe links" |
| Die Arbeit | quarterly magazine | GLB trade-union publication |
| Weg & Ziel | magazine | re-launched in print in 2026 by KPÖ |

#### B. Left / centre-left / left-liberal

| Title | Publication form | Notes |
| --- | --- | --- |
| Der Standard | daily newspaper | euro|topics: linksliberal; current ÖAK metric recorded |
| Falter | weekly newspaper | euro|topics: linksliberal |
| Augustin | street newspaper | Vienna social/street newspaper |
| Datum | magazine | euro|topics: linksliberal |
| an.schläge | magazine | feminist print magazine, seven 2026 issues |
| Arbeit&Wirtschaft | magazine | six print issues/year; labour perspective |
| MO – Magazin für Menschenrechte | quarterly magazine | SOS Mitmensch; 2026 media data available |
| INTERNATIONAL | magazine | six print issues/year; international affairs |

#### C. Liberal / centre / economically liberal

| Title | Publication form | Notes |
| --- | --- | --- |
| Kleine Zeitung | daily newspaper | euro|topics: liberal; current ÖAK metric recorded |
| Oberösterreichische Nachrichten | daily newspaper | independent regional daily; current ÖAK metric recorded |
| Tiroler Tageszeitung | daily newspaper | current ÖAK metric recorded |
| Vorarlberger Nachrichten | daily newspaper | current ÖAK metric recorded |
| profil | weekly magazine | euro|topics: liberal; current ÖAK metric recorded |
| trend | magazine | euro|topics: economically liberal |
| Der Pragmaticus | magazine | active 2026 print |
| GEWINN | magazine | current ÖAK and Media-Analyse metrics recorded |
| NEWS | magazine | active print |

#### D. Conservative / liberal-conservative / Christian

| Title | Publication form | Notes |
| --- | --- | --- |
| Die Presse | daily newspaper | euro|topics: liberal-conservative; current ÖAK metric recorded |
| Kurier | daily newspaper | euro|topics: liberal-conservative; current ÖAK metric recorded |
| Salzburger Nachrichten | daily newspaper | euro|topics: Christian; current ÖAK metric recorded |
| Die Furche | weekly newspaper | euro|topics: Christian |
| Österreichische BauernZeitung | weekly newspaper | active 2026 |

The nationally relevant conservative/christian Austrian print market contains substantially more newspapers than clearly classifiable general-political magazines. FSC records the gap instead of filling it with lifestyle or association magazines.

#### E. Right / right-conservative / right-libertarian

| Title | Publication form | Notes |
| --- | --- | --- |
| ZurZeit | weekly newspaper | self-description: wertkonservativ and freisinnig |
| Neue Freie Zeitung | weekly newspaper | FPÖ party newspaper; imprint documents ownership/role |
| Kärntner Nachrichten | periodical | FPÖ Kärnten publication; current print status to be rechecked before activation |
| FREILICH | bimonthly magazine | publisher self-description: conservative opinion magazine |

The general-interest Austrian right-wing print market is smaller than the mainstream market. Party/regional publications may be cataloged, but magazines are not relabelled as newspapers to meet a quota.

#### F. Radical right / externally classified extreme-right spectrum

| Title | Publication form | Notes |
| --- | --- | --- |
| Info-DIREKT | magazine | DÖW externally classifies the publication as extreme-right |
| Der Eckart | magazine | DÖW classifies publisher ÖLM as extreme-right and identifies Der Eckart as its periodical |
| Abendland | periodical | current print/activity and classification provenance to be rechecked before activation |

This segment is predominantly magazine/periodical-form in the current Austrian print market. The catalog records that asymmetry explicitly.

#### G. Boulevard / mass reach

Boulevard is a **format dimension**, not a political orientation.

| Title | Publication form | Notes |
| --- | --- | --- |
| Kronen Zeitung | daily newspaper / boulevard | very high national reach; current ÖAK/MA metrics recorded |
| Heute | free daily / boulevard | 501,409 distributed copies in ÖAK H1 2026 |
| ÖSTERREICH / oe24 | paid + free daily hybrid / boulevard | current 2026 print operation and cross-media metrics recorded |

## Switzerland (CH)

### Print

Switzerland is a separate multilingual country block. Each catalog entry stores its own article/publication language; the initial print catalog covers German, French, Italian and Romansh.

All entries below are catalog candidates only; no feed is activated by catalog inclusion.

#### A. Radical / system-oppositional left

| Title | Language | Publication form | Notes |
| --- | --- | --- | --- |
| solidaritéS | fr | periodical / newspaper | anticapitalist, feminist, ecosocialist self-positioning; active 2026 |
| Voix Populaire | fr | magazine | affiliated with Romandy labour/POP structures |
| WIDERSPRUCH | de | periodical | self-description: Beiträge zu sozialistischer Politik |
| Neue Wege | de | magazine | religious-socialist / critical tradition; active 2026 |

The current Swiss radical-left print market is predominantly periodical/magazine-form. FSC records the real asymmetry rather than relabelling titles.

#### B. Left / centre-left / left-liberal

| Title | Language | Publication form | Notes |
| --- | --- | --- | --- |
| WOZ – Die Wochenzeitung | de | weekly newspaper | euro|topics: left |
| Tages-Anzeiger | de | daily newspaper | euro|topics: left-liberal |
| Le Courrier | fr | daily newspaper | euro|topics: left |
| Le Temps | fr | daily newspaper | euro|topics: left-liberal |
| Tribune de Genève | fr | daily newspaper | euro|topics: left-liberal |
| laRegione | it | daily newspaper | euro|topics: left-liberal |
| SonntagsZeitung | de | Sunday newspaper | euro|topics: left-liberal |
| Le Matin Dimanche | fr | Sunday newspaper | euro|topics: left-liberal |
| Beobachter | de | magazine | euro|topics: left-liberal |

#### C. Liberal / centre / economically liberal

| Title | Language | Publication form | Notes |
| --- | --- | --- | --- |
| Aargauer Zeitung | de | daily newspaper | euro|topics: liberal |
| NZZ am Sonntag | de | Sunday newspaper | euro|topics: liberal |
| Handelszeitung | de | weekly newspaper | euro|topics: economically liberal |
| Corriere del Ticino | it | daily newspaper | euro|topics: liberal |
| Schweizer Monat | de | magazine | liberal publisher self-positioning; active 2026 |
| Nebelspalter | de | magazine | publisher self-positioning: liberal / bourgeois |
| BILANZ | de | magazine | current WEMF/MACH metrics recorded |
| PME | fr | magazine | current WEMF/MACH metrics recorded |

#### D. Conservative / liberal-conservative / bourgeois-conservative

| Title | Language | Publication form | Notes |
| --- | --- | --- | --- |
| Neue Zürcher Zeitung | de | daily newspaper | euro|topics: liberal-conservative |
| Luzerner Zeitung | de | daily newspaper | euro|topics: liberal-conservative |
| St. Galler Tagblatt | de | daily newspaper | euro|topics: liberal-conservative |
| Schweizerzeit | de | magazine | publisher self-description: bürgerlich-konservativ; monthly print since 2026 |

The current general-political Swiss conservative magazine market is smaller than the newspaper market; the catalog keeps that gap explicit.

#### E. Right / right-conservative / party press

| Title | Language | Publication form | Notes |
| --- | --- | --- | --- |
| Die Weltwoche | de | weekly newspaper | euro|topics: right |
| SVP-Klartext | de | party newspaper / periodical | current SVP party newspaper; dated 2026 tariff reports about 50,500 copies and publisher page reports 100,000 readers |

#### F. Far-right / radical-right external positioning

| Title | Language | Publication form | Notes |
| --- | --- | --- | --- |
| Schweizer Demokrat | de | party newspaper / periodical | Historisches Lexikon der Schweiz historically locates the party far right; current party newspaper remains active |

The historical "far right" positioning is stored as attributed external metadata. It is **not** treated as synonymous with a current official extremist classification.

#### G. General-interest / linguistically important print

No political classification is forced when reliable provenance is absent or unnecessary for the catalog role.

| Title | Language | Publication form | Notes |
| --- | --- | --- | --- |
| La Quotidiana | rm | daily newspaper | only Romansh daily newspaper; ensures Romansh representation |
| Schweizer Illustrierte | de | magazine | current WEMF/MACH metrics recorded |
| L’illustré | fr | magazine | current WEMF/MACH metrics recorded |
| Das Magazin | de | weekly magazine | current publisher/MACH metrics recorded |

#### H. Boulevard / mass reach

Boulevard is a **format dimension**, not a political orientation.

| Title | Language | Publication form | Notes |
| --- | --- | --- | --- |
| Blick | de | daily newspaper / boulevard | current WEMF/MACH metrics recorded |
| SonntagsBlick | de | Sunday newspaper / boulevard | current WEMF/MACH metrics recorded |

The print editions of **20 Minuten / 20 minutes / 20 minuti ended in December 2025**. They therefore do not belong in the active 2026 Swiss print catalog, even though their digital brands remain relevant for a later digital-media block.

## International comparison set

The international print catalog is **not** a world-coverage catalog. It is a Germany-focused comparison set for cross-source story, claim, perspective and coverage analysis.

Selection prioritises:

- relevance to German foreign, economic or security policy;
- international agenda-setting role;
- incremental editorial or political perspective value;
- media-system comparison value, including state/party-controlled media;
- active recurring print status.

There are no country quotas and no requirement to populate every FSC political group. Country-specific political labels are not force-mapped onto the FSC left-right axis. Political group assignment requires at least two independent external sources that materially agree on the relevant left-right direction.

State-owned, party-official and substantially state-funded media may be included when they add relevant comparison value. Control, ownership and funding are stored as attributed media-positioning metadata and do not substitute for political classification.

The current curated core contains 35 active print titles from Argentina, Australia, Brazil, Canada, China, Egypt, India, Israel, Japan, Mexico, Nigeria, Singapore, South Africa, South Korea and Türkiye. Additional researched titles remain documented as deferred candidates and may be activated for topic-specific expansion without implying that the current core is incomplete.

Taiwan and Hong Kong are currently deferred. FSC will not overload the existing ISO country field with politically sensitive media-market geography until a more explicit geography model is available.

## Coverage policy

The target of at least 3–5 titles per political segment and publication-form group is a **research coverage goal, not a quota**. FSC retains genuine market asymmetries when fewer reliably classifiable active print titles exist. Titles must not be moved, broadened or politically classified merely to satisfy a numeric target. Missing coverage remains explicit and can trigger further source research.

## Reach and circulation model

Metrics are historical observations, not properties overwritten on the source.

Required fields are represented by the provenance-aware `SourceMetric` model:

- metric kind (sold circulation, distributed circulation, print run, print readers, digital unique users, visits, page impressions, paid digital subscriptions, subscribers, radio daily listeners, radio hourly listeners, radio market share, TV viewers, TV daily reach, TV market share)
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
- Print circulation, readers, digital unique users, visits, page impressions, radio listeners and television audience metrics remain separate metrics.
- Radio and television market shares use basis points as the integer unit (for example, 1.7% = 170 basis points), with target audience and measurement definition preserved in metric scope.
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

## Catalog-block progress

Completed print catalog blocks:

1. Germany (DE)
2. Austria (AT)
3. Switzerland (CH)
4. Great Britain (GB)
5. United States (US)
6. Europe comparison set outside DE/AT/CH/GB
7. Germany-focused international comparison set outside Europe and the US

Foreign-language media are part of the current product scope. Catalog completeness is defined by comparative value and provenance, not by world or country coverage.

## Activation rule

A catalog entry may only receive active production feeds after joint source review. Building the catalog, metadata model, provenance records and technical feed validation does not itself authorize activation.
