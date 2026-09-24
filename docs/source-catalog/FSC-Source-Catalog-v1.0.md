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

## Germany (DE) – National broadcast

Germany's national broadcast catalog follows the same A–F research matrix as print, but television and radio are counted separately. The target of 3–5 Sources per political planning segment and broadcast form is a research goal, not a quota.

Source identity is editorial rather than channel-based: one newsroom/editorial source may have several television or radio outlets. Programme names and channel editions never count as independent Sources merely because they are separately branded. Regional broadcasters and regional/private radio brands are excluded from this national block and will be reviewed in a dedicated DE regional block.

The jointly approved national candidate core contains 14 editorial Sources:

| Planning segment | Television Sources | Radio Sources |
| --- | --- | --- |
| A radical/system-oppositional left | explicit market gap | explicit market gap |
| B left/centre-left/left-liberal | explicit market gap | Deutschlandradio (B/C research boundary; DLF/Kultur/Nova are outlets) |
| C liberal/centre | ARD-aktuell, ZDF, RTL NEWS, :newstime | RTL NEWS, Klassik Radio |
| D conservative/liberal-conservative research pool | WELT, IDEA, EWTN Deutschland, Hope TV Deutsch | ERF, radio horeb |
| E right/right-conservative/right-libertarian | explicit market gap | Kontrafunk, NIUS |
| F radical right | explicit market gap | explicit market gap |

The planning table is not itself a persisted FSC ideology classification. Persisted political group assignment still requires at least two independent external sources that materially agree in left/right direction.

Specific identity rules:

- **Deutschlandradio** is one Source. Deutschlandfunk, Deutschlandfunk Kultur and Deutschlandfunk Nova are radio outlets/programmes.
- **RTL NEWS** is one editorial Source. RTL Aktuell, ntv and RTL Radio news are outlets and do not count as three independent confirmations.
- **:newstime** is one Source for the centrally produced news editions on SAT.1, ProSieben and Kabel Eins.
- **WELT TV** extends the existing WELT Source already present in the DE print catalog; it must not create a second WELT Source.
- **NIUS – Das Radio** is an outlet of the cross-media NIUS Source; a later digital catalog must extend the same Source.
- Religious or worldview-oriented broadcasters may enter the research pool when politics and society are recurring editorial subjects. Religious/theological positioning is stored separately and never automatically converted into a political classification.
- **REGIOCAST Nachrichten** is treated as a future agency/content-supplier candidate rather than a consumer-facing radio Source.
- **phoenix** is deferred because its joint ARD/ZDF structure exposes a limitation in the current scalar ownership-based consensus-independence key. It should be revisited when independence grouping is modeled explicitly.

No feed is activated by inclusion in this catalog.

## Germany (DE) — Regional broadcast

This regional block covers state-level and multi-state editorial Sources. Local/city television and local radio are deliberately deferred to a later DE local block. Television and radio are counted separately for coverage, but FSC counts editorial Sources rather than individual programme brands.

The jointly approved compact regional core contains 19 editorial Source identities:

| Planning segment | Television Sources | Radio Sources |
| --- | --- | --- |
| A radical/system-oppositional left | explicit market gap | explicit market gap |
| B left/centre-left/left-liberal | explicit market gap | explicit market gap |
| C public-service regional reference | BR, hr, MDR, NDR, Radio Bremen, rbb, SR, SWR, WDR | BR, hr, MDR, NDR, Radio Bremen, rbb, SR, SWR, WDR |
| D conservative/liberal-conservative | explicit market gap | explicit market gap |
| E right/right-conservative/right-libertarian | explicit market gap | explicit market gap |
| F radical right / externally classified extreme-right spectrum | explicit market gap | explicit market gap |

Politically unclassified private Sources: RTL Nord, RTL WEST, RTL Hessen, SAT.1 Norddeutschland, SAT.1 Bayern, ANTENNE BAYERN, FFH Newsredaktion, radio ffn, R.SH and radio SAW.

The C placement of the nine ARD Landesrundfunkanstalten is a public-service regional reference convention only and is not a persisted political classification.

Specific identity rules:
- **BR, hr, MDR, NDR, Radio Bremen, rbb, SR, SWR and WDR are nine Sources.** Their television and radio programme brands are outlets, not independent Sources.
- **RTL Nord** is one Source with two regional editions for Hamburg/Schleswig-Holstein and Niedersachsen/Bremen.
- **SAT.1 Norddeutschland** is one Source with two regional editions for Hamburg/Schleswig-Holstein and Niedersachsen/Bremen.
- **RTL WEST, RTL Hessen and SAT.1 Bayern** remain separate from the national RTL NEWS and :newstime Sources because they have their own regional programme/editorial responsibility.
- **FFH Newsredaktion** is one news Source serving HIT RADIO FFH, planet radio and harmony; the consumer radio brands do not count as three independent newsrooms.
- **R.SH** is the regional consumer-facing Source. **REGIOCAST Nachrichten** remains deferred to the Agency/Content Supplier model.
- ANTENNE BAYERN, radio ffn and radio SAW are independent statewide private radio Sources.
- Private regional Sources remain politically unclassified until two independent external sources support a Source-level political direction.
- Local television such as münchen.tv, Hamburg 1, TV.Berlin, Franken Fernsehen, Regio TV and Niederbayern TV, plus local/city radio, remain outside this compact regional block.

No feed is activated by inclusion in this catalog.

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

### National broadcast candidate core

Television and radio are reviewed separately, but FSC counts **editorially independent Sources**, not channels or programmes. The research target remains 3–5 Sources per A–F planning segment and broadcast form; it is a goal, never a quota. Genuine Austrian market gaps remain explicit.

The jointly approved AT-national core contains eight editorial Sources:

| Planning segment | Television Sources | Radio Sources |
| --- | --- | --- |
| A radical/system-oppositional left | explicit market gap | explicit market gap |
| B left/centre-left/left-liberal | explicit market gap | explicit market gap; FM4 is an ORF outlet, not an independent Source |
| C liberal/centre | ORF Information, ProSiebenSat.1 PULS 4 Newsroom | ORF Information, inforadio, kronehit |
| D conservative/liberal-conservative research pool | explicit market gap | Radio Maria Österreich |
| E right/right-conservative/right-libertarian | ServusTV | explicit market gap |
| F radical right / externally classified extreme-right spectrum | AUF1 | explicit market gap |

The planning table is not itself a persisted FSC ideology classification. Persisted political group assignment still requires at least two independent external sources that materially agree in left/right direction.

Specific identity rules:

- **ORF Information** is one cross-media Source. The ORF multimedial newsroom bundles current news production across television, radio and online; ORF 1, ORF 2, ORF III, Ö1, Ö3 and FM4 are outlets/programmes for FSC independence counting.
- **ProSiebenSat.1 PULS 4 Newsroom** is one Source for the centrally coordinated current-news operation serving PULS 24, PULS 4 and ATV.
- **ÖSTERREICH / oe24** already exists in the AT print catalog. **oe24.TV** and **oe24 RADIO** extend that same Source and therefore do not create a ninth Source. Its political A–F placement remains explicitly unclassified until sufficient independent provenance exists.
- **Radio Maria Österreich** enters the research pool because politics and society recur in its editorial programme. Catholic/religious identity is stored separately and is not automatically converted into a political classification.
- **ServusTV** has one external right-leaning classification in the current provenance set. Its E position is research planning only; it does not yet satisfy the two-source rule for persisted political assignment.
- **AUF1** has two independent external sources materially agreeing on right-extremist-spectrum placement; the exact terminology used by each classifier remains preserved.
- **ERF Süd** is deferred as an Austrian Source because ERF Medien Österreich states that the programme currently comes predominantly from South Tyrol and Germany. National Austrian DAB+ carriage alone does not establish an independent Austrian newsroom.
- **Kontrafunk** and **Klassik Radio** are not duplicated into Austria merely because they are receivable there.
- **Krone.tv** is deferred for a later cross-media outlet review of the existing Kronen Zeitung Source rather than being created as an independent Source.
- Regional Austrian television and radio remain outside this national block and will be reviewed separately.

No feed is activated by inclusion in this catalog.

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

### National broadcast candidate core

Television and radio are reviewed separately, while FSC counts editorial Sources rather than channels, programmes or transmission windows. The research target remains 3–5 independent Sources per A–F planning segment and broadcast form; it is a goal, never a quota.

The jointly approved CH-national core contains 13 Source identities: eight new Swiss Sources and five extensions/reuses of Sources already present elsewhere in the catalog.

| Planning segment | Television Sources | Radio Sources |
| --- | --- | --- |
| A radical/system-oppositional left | explicit market gap | explicit market gap |
| B left/centre-left/left-liberal | SonntagsZeitung | explicit market gap |
| C liberal/centre/public-service reference | SRF, RTS | SRF, RTS |
| D conservative/liberal-conservative | Neue Zürcher Zeitung | explicit market gap |
| E right/right-conservative/right-libertarian | explicit market gap | Kontrafunk |
| F radical right / externally classified extreme-right spectrum | Kla.TV | explicit market gap |

Politically unclassified but included for national broadcast relevance: RSI, RTR, BILANZ, Blick, ERF Medien Schweiz, ALPHAVISION and Radio Maria Deutschschweiz.

The planning table is not itself a persisted FSC ideology classification. Persisted political group assignment requires at least two independent external sources that materially agree in left/right direction.

Specific identity rules:
- **SRF, RTS, RSI and RTR are four Sources**, not one SRG Source. SRG is the common parent; journalistic responsibility for Information, Culture, Entertainment and Society/Knowledge remains in the language-region units.
- **PresseTV is not a Source** for FSC. NZZ Format, NZZ Standpunkte, BILANZ Standpunkte and SonntagsZeitung Standpunkte remain products of the respective media houses.
- **Blick TV** extends the existing Blick Source rather than creating a separate audiovisual newsroom.
- **Kontrafunk** is reused from the existing DE broadcast catalog. Swiss domicile and Switzerland-focused programming do not create a second Source.
- **FENSTER ZUM SONNTAG** is deliberately split by editorial responsibility: ALPHAVISION owns the Magazin editorial responsibility; ERF Medien Schweiz owns the Talk editorial responsibility and also operates Radio Life Channel.
- **Radio Maria Deutschschweiz** is included as a national religious radio Source but remains politically unclassified. Religious identity is not automatically conservative.
- **Kla.TV** is a Swiss-origin online-television Source. Its F research placement is based on two independent external journalistic assessments and is not presented as an official Swiss extremism designation.
- **RSI and RTR** remain politically unclassified pending sufficient independent orientation provenance.
- BAKOM-licensed local radio and regional television remain outside this national block for a later CH regional review.
- The 3+ entertainment-led sender family and Weltwoche Daily are not relabelled as general-political broadcast Sources merely because they distribute audiovisual content.

No feed is activated by inclusion in this catalog.

## Great Britain (GB) — National broadcast

The GB national broadcast catalog uses the same A–F research matrix, but counts television and radio separately and counts editorial newsrooms rather than channels, common owners, production companies or transmission suppliers. The research target remains 3–5 independent Sources per segment and medium; it is a goal, never a quota.

The jointly approved GB-national core contains 14 editorial Source identities:

| Planning segment | Television Sources | Radio Sources |
| --- | --- | --- |
| A radical/system-oppositional left | explicit market gap | explicit market gap |
| B left/centre-left/left-liberal | Channel 4 News | explicit market gap |
| C liberal/centre/public-service and mainstream reference | BBC News, ITV News, 5 News, Sky News | BBC News, BBC Radio 5 Live |
| D conservative/liberal-conservative | explicit market gap | explicit market gap |
| E right/right-conservative/right-libertarian | GB News | GB News |
| F radical right / externally classified extreme-right spectrum | explicit market gap | explicit market gap |

Politically unclassified but included for national broadcast relevance: Revelation TV, LBC, LBC News, Times Radio, Talk, UCB and Premier Christian Radio.

The planning table is not itself a persisted FSC ideology classification. Persisted political group assignment requires at least two independent external sources that materially agree in left/right direction.

Specific identity rules:
- **ITV News, Channel 4 News and 5 News are three Sources**, despite common production by ITN. ITN itself describes them as separate newsrooms with distinct editorial voices and missions.
- **BBC News** is one cross-media news Source for central television news and BBC Radio 4 news/current-affairs programmes produced by BBC News.
- **BBC Radio 5 Live** is a separate Source because it has its own station-level controller, commissioning and editorial structure.
- **LBC and LBC News are separate Sources**. Shared Global newsroom infrastructure and bulletins do not collapse the two national speech/news services into one editorial Source.
- **Times Radio is a separate Source from The Times**. It draws on Times/Sunday Times journalism but has its own Programme Director, schedule, production operation and editorial contacts; no political classification is inherited from the print title.
- **GB News** is one cross-media Source with television and GB News Radio as outlets.
- **UCB** is one Source with UCB 1 and UCB 2 as radio outlets.
- **Sky News Radio** is deferred to the later Agency/Content Supplier model because it primarily supplies bulletins to commercial radio stations rather than operating as a normal national consumer radio programme.
- **Talk** is included as a current national radio/digital Source; the former linear TalkTV channel is not treated as a current television Source.
- Christian broadcasters may enter the catalog when news, politics or society are recurring editorial subjects. Christian identity is never automatically mapped to D or any other political segment.
- Local, regional and devolved broadcasters, including BBC Local Radio, STV and S4C, remain outside this national block for later GB regional/devolved review.
- Digital-native audiovisual outlets such as Novara Media remain for a later digital-video/podcast block.

No feed is activated by inclusion in this catalog.

## United States (US) — National broadcast

The US national broadcast catalog uses the same A–F research matrix, but counts television and radio separately and counts editorial Sources rather than networks of affiliates, content-supply feeds, simulcasts or distribution platforms. The research target remains 3–5 independent Sources per segment and medium; it is a goal, never a quota.

The jointly approved US-national core contains 17 editorial Source identities:

| Planning segment | Television Sources | Radio Sources |
| --- | --- | --- |
| A radical/system-oppositional left | explicit market gap | explicit market gap |
| B left/centre-left/left-liberal | Democracy Now!, PBS NewsHour, MS NOW, CNN | Democracy Now!, NPR |
| C liberal/centre/mainstream reference | ABC News, CBS News, NBC News, NewsNation | SiriusXM POTUS |
| D conservative/liberal-conservative | explicit market gap | explicit market gap |
| E right/right-conservative/right-libertarian | Fox News | explicit market gap |
| F radical right / externally classified far-right spectrum | One America News | explicit market gap |

Politically unclassified but included for national broadcast relevance: Newsmax, EWTN, SiriusXM Progress, SiriusXM Patriot and American Family Radio.

The planning table is not itself a persisted FSC ideology classification. Persisted political group assignment requires at least two independent external sources that materially agree in left/right direction. Conflicting external radicality labels remain unresolved rather than being force-mapped into E or F.

Specific identity rules:
- **Democracy Now!** is one cross-media Source syndicated through television and radio carriers; carrier stations do not become new Sources.
- **PBS NewsHour** is the editorial Source. PBS distribution/member-station carriage does not make PBS as a whole the Source.
- **MS NOW and NBC News are separate Sources** after the Versant separation completed in 2026.
- **NPR** is one Source; Morning Edition, All Things Considered and Weekend Edition are programme outlets/formats, while local member stations remain regional.
- **Fox News** is one national television Source; Fox News Radio affiliate bulletins and SiriusXM simulcasts do not create another Source.
- **One America News (OAN)** is placed in F only because two independent external sources explicitly classify it in the far-right spectrum; this is not an official extremism designation.
- **Newsmax remains outside E/F** despite a clearly rightward external orientation because current independent sources disagree on radicality: some classify it Right, while peer-reviewed research treats it as a far-right outlet.
- **SiriusXM POTUS, Progress and Patriot are three separately programmed Sources**. POTUS is a C/reference candidate; Progress and Patriot remain politically unclassified because operator self-positioning alone does not satisfy the two-source rule.
- **EWTN** is one cross-media Source for national television and radio. Catholic identity is not automatically mapped to D or E.
- **American Family Radio** is included for recurring news, politics and social-issues programming, but evangelical identity is not automatically mapped politically.
- **ABC News Radio** and **Fox News Radio** are deferred to the later Agency/Content Supplier model.
- **CBS News Radio** is excluded from the active core because the service ended on May 22, 2026.
- **C-SPAN/C-SPAN Radio** are deferred to an institutional/public-affairs primary-source block.
- **CNBC, Bloomberg and Fox Business** are deferred to a specialist economic/financial source block.
- Local network affiliates, regional public-media stations and local talk radio remain outside this national block for later US regional review.

No feed is activated by inclusion in this catalog.

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

## Source identity and product outlets

FSC counts an editorially independent newsroom or editorial brand as the Source, not every edition, channel or programme. Multiple products of the same editorial source are modeled as SourceOutlets. Shared ownership alone does not merge editorially independent newsrooms.

Examples: Guardian Weekly is an outlet/product of The Guardian; SonntagsBlick is an outlet/product of Blick. By contrast, independently edited Sunday titles such as NZZ am Sonntag or SonntagsZeitung may remain separate Sources when they have materially independent editorial leadership.

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

Completed catalog blocks:

1. Germany (DE)
2. Austria (AT)
3. Switzerland (CH)
4. Great Britain (GB)
5. United States (US)
6. Europe comparison set outside DE/AT/CH/GB
7. Germany-focused international comparison set outside Europe and the US
8. Germany national broadcast candidate core (TV and radio; regional broadcast separate)
9. Austria national broadcast candidate core (TV and radio; regional broadcast separate)
10. Switzerland national broadcast candidate core (TV and radio; regional broadcast separate)
11. Great Britain national broadcast candidate core (TV and radio; regional/devolved broadcast separate)
12. United States national broadcast candidate core (TV and radio; regional broadcast separate)
13. Germany regional broadcast candidate core (state/multi-state level; local broadcast separate)

Foreign-language media are part of the current product scope. Catalog completeness is defined by comparative value and provenance, not by world or country coverage.

## Activation rule

A catalog entry may only receive active production feeds after joint source review. Building the catalog, metadata model, provenance records and technical feed validation does not itself authorize activation.
