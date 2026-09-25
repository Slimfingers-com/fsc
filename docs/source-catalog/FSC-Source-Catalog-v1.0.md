# FSC Source Catalog v1.0

Status: working catalog for joint review. Catalog inclusion does **not** activate ingestion.

## Catalog rules

FSC keeps these dimensions separate:

1. **Country of origin** — country blocks are never merged. Germany, Austria and Switzerland are separate.
2. **Media category** — print, broadcast, digital, agency, primary source, organization, other.
3. **Publication form** — e.g. daily newspaper, weekly newspaper, magazine, periodical, radio, television, digital-native.
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

The jointly approved national candidate core contains 15 editorial Sources:

| Planning segment | Television Sources | Radio Sources |
| --- | --- | --- |
| A radical/system-oppositional left | explicit market gap | explicit market gap |
| B left/centre-left/left-liberal | explicit market gap | Deutschlandradio (B/C research boundary; DLF/Kultur/Nova are outlets) |
| C liberal/centre | ARD-aktuell, ZDF, phoenix, RTL NEWS, :newstime | RTL NEWS, Klassik Radio |
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
- **REGIOCAST Nachrichten** is modeled in the Agency/Content Supplier catalog as its own supplier Source rather than as a consumer-facing radio Source.
- **phoenix** is its own Source in the C public-service reference pool. Its joint ARD/ZDF structure is documented without a static collapsing SourceRelation: linking phoenix statically to both ARD-aktuell and ZDF would transitively collapse those otherwise independent Sources. Concrete shared, supplied or co-produced content affects independence only through verified ArticleProvenance.

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
- **R.SH** is the regional consumer-facing Source. **REGIOCAST Nachrichten** is a separate supplier Source in the Agency/Content Supplier catalog; supplier provenance must be attached per article before it affects independence.
- ANTENNE BAYERN, radio ffn and radio SAW are independent statewide private radio Sources.
- Private regional Sources remain politically unclassified until two independent external sources support a Source-level political direction.
- Local television such as münchen.tv, Hamburg 1, TV.Berlin, Franken Fernsehen, Regio TV and Niederbayern TV, plus local/city radio, remain outside this compact regional block.

No feed is activated by inclusion in this catalog.

## Germany (DE) — Digital

Digital is modeled as a **medium**, not as a synonym for born-digital. Born-digital Sources use the `digital_native` publication form. Websites of Sources already cataloged in print or broadcast extend the existing Source and use a generic digital outlet form instead of creating duplicate Source identities.

The jointly approved DE digital candidate set contains 36 digital candidates: 29 in the A–F research-planning core and seven politically unclassified/specialist candidates. Of those 36 candidates, 20 create new Source identities and 16 extend Sources that already exist elsewhere in the FSC catalog.

| Planning segment | Digital Sources |
| --- | --- |
| A radical/system-oppositional left | Klasse Gegen Klasse, Perspektive Online, Lower Class Magazine, NachDenkSeiten, junge Welt |
| B left/centre-left/left-liberal | CORRECTIV, watson.de, taz, DER SPIEGEL, DIE ZEIT |
| C liberal/centre/reference | t-online, Krautreporter, The Pioneer, ARD-aktuell / tagesschau.de, ZDF / ZDFheute |
| D conservative/liberal-conservative | Frankfurter Allgemeine Zeitung, WELT, BILD, FOCUS, Cicero |
| E right/right-conservative/right-libertarian | Achgut, Apollo News, reitschuster.de, NIUS, Tichys Einblick |
| F radical right / externally classified extreme-right spectrum | PI-News, COMPACT, Sezession, ZUERST! |

The A–F table is a research-planning matrix, not a persisted FSC political classification. Persisted Source-level political or radicality assignments still require two independent external sources that materially agree.

Politically unclassified/specialist digital candidates: netzpolitik.org, Übermedien, Table.Briefings, Volksverpetzer, Belltower.News, Multipolar and apolut.

Specific identity rules:

- **junge Welt, taz, DER SPIEGEL, DIE ZEIT, Frankfurter Allgemeine Zeitung, WELT, BILD, FOCUS, Cicero, Tichys Einblick, COMPACT, Sezession and ZUERST!** extend their existing print Sources.
- **ARD-aktuell / tagesschau.de** and **ZDF / ZDFheute** extend the existing national broadcast Sources.
- **NIUS** extends the existing cross-media Source already used for NIUS – Das Radio.
- **NachDenkSeiten** remains an explicit A/B research-boundary case and is kept in the A planning pool by joint decision; catalog placement does not create a radicality classification.
- **Multipolar** and **apolut** are deliberately retained as politically unclassified candidates rather than force-mapped into A–F.
- Born-digital Sources use `publication_form=digital_native`; web outlets extending an existing print/broadcast Source use `publication_form=other` under `media_category=digital`.
- Foreign-origin digital media are not relabeled as German Sources solely because they publish in German or target German audiences.
- Aggregators and distribution platforms are not editorial Sources.

No feed is activated by inclusion in this catalog.

## Germany (DE) — Primary Sources

Primary Sources are grouped by **institutional function**, not political orientation. They use `SourceType.PRIMARY_SOURCE`, `media_category=primary_source` and `publication_form=other`. Under ADR 0021 they remain full content/evidence Sources but do not contribute to independent editorial-confirmation counts.

The jointly approved DE primary-source core contains 30 Source identities:

| Functional group | Primary Sources |
| --- | --- |
| Constitutional organs / legislature | Deutscher Bundestag, Bundesrat, Bundespräsident |
| Federal government / foreign affairs / security | Bundesregierung / Bundespresseamt, Auswärtiges Amt, Bundesministerium des Innern, Bundesministerium der Verteidigung |
| Federal government / economy / social affairs | Bundesministerium der Finanzen, Bundesministerium für Wirtschaft und Energie, Bundesministerium für Arbeit und Soziales, Bundesministerium für Gesundheit |
| Official data / statistics | Statistisches Bundesamt (Destatis), Bundesagentur für Arbeit, Deutsche Bundesbank, Bundeswahlleiterin, Robert Koch-Institut |
| Federal courts | Bundesverfassungsgericht, Bundesgerichtshof, Bundesverwaltungsgericht |
| Economic / infrastructure regulators | Bundesnetzagentur, Bundeskartellamt, BaFin |
| Security / migration authorities | Bundeskriminalamt, Bundesamt für Verfassungsschutz, Bundesamt für Migration und Flüchtlinge |
| Parliamentary political actors | CDU/CSU-Fraktion, AfD-Fraktion, SPD-Bundestagsfraktion, Bündnis 90/Die Grünen Bundestagsfraktion, Fraktion Die Linke |

Specific identity and attribution rules:

- **Institution, not website/portal, is the Source.** DIP, press archives, statistics portals and document repositories are distribution Outlets, not separate Source identities.
- A document hosted by Bundestag/DIP is attributed to its **substantive author** when identifiable. A faction motion therefore belongs to that faction Source, not automatically to Deutscher Bundestag.
- **Bundesregierung / Bundespresseamt and individual federal ministries remain separate Sources.** Republishing a ministry statement on bundesregierung.de does not create a second independent confirmation; article provenance can represent the republication chain.
- Parliamentary factions are primary political actors and receive no FSC political-orientation classification from their institutional role.
- The initial core uses Bundestag factions rather than duplicating both party organizations and factions. Party organizations remain eligible for a later dedicated expansion.
- Additional federal ministries remain eligible for topic-specific expansion; the initial core focuses on the most frequently relevant national policy domains.
- Inclusion as a Primary Source never allows an institution to corroborate its own assertion for Consensus/Coverage independence.

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

## Austria (AT) — Regional broadcast

This block covers state-level and multi-state regional editorial Sources. Technical reach alone does not make a regional editorial Source national.

The jointly approved compact core contains 19 Source identities:

| Planning segment | Television Sources | Radio Sources |
| --- | --- | --- |
| A radical/system-oppositional left | explicit market gap | explicit market gap |
| B left/centre-left/left-liberal | explicit market gap | explicit market gap |
| C public-service regional reference | 9 ORF Landesstudios | the same 9 ORF Landesstudios |
| D conservative/liberal-conservative | explicit market gap | explicit market gap |
| E right/right-conservative/right-libertarian | explicit market gap | explicit market gap |
| F externally classified extreme-right spectrum | RTV Regionalfernsehen OÖ | explicit market gap |

Politically unclassified private Sources: W24, LT1, Kanal3, RTS Regionalfernsehen Salzburg, Tirol TV, Antenne Steiermark, Life Radio, Radio U1 Tirol and Radio 88.6.

Specific identity rules:

- **The nine ORF Landesstudios are nine regional Sources**, each combining its regional television, radio and digital newsroom output. They remain separate from the national ORF Information Source.
- **R9 is not a collective Source** for its partner stations. Partner broadcasters retain their editorial Source identity; genuinely R9-produced formats can be reviewed separately later.
- **RTV Regionalfernsehen OÖ** is placed in F using two independent external sources, including the Austrian Verfassungsschutzbericht 2025. This is attributed external classification, not an FSC legal designation.
- **Radio 88.6** remains a multi-state regional Source despite nationwide DAB+ availability because Source scope follows editorial mandate, not technical reach alone.
- **KURIER TV** is deferred as a future outlet extension of the existing Kurier Source, not a new Source.
- N1 TV, KT1 and Ländle TV remain legitimate deferred regional candidates; no federal-state quota applies.
- Smaller local/community broadcasters remain outside this block for later AT local review.

No feed is activated by inclusion in this catalog.

## Austria (AT) — Digital

Digital is modeled as a **medium**. Born-digital Sources use the `digital_native` publication form. Existing print/broadcast Sources are extended rather than duplicated; digital continuations of historic print identities may use `publication_form=other` when they are not born-digital.

The jointly approved AT digital candidate set contains 31 candidates: 24 in the A–F research-planning core and seven politically unclassified/specialist candidates. Of those, 10 create new Source identities and 21 extend existing Sources.

| Planning segment | Digital Sources |
| --- | --- |
| A radical/system-oppositional left | Der Funke, Die Rote Fahne, Volksstimme |
| B left/centre-left/left-liberal | Der Standard, Falter, MOMENT.at |
| C liberal/centre/reference | ORF Information / ORF.at, ProSiebenSat.1 PULS 4 Newsroom / PULS24.at, Kleine Zeitung, profil, WZ / Wiener Zeitung |
| D conservative/liberal-conservative | Die Presse, Kurier, Salzburger Nachrichten, Die Furche |
| E right/right-conservative/right-libertarian | eXXpress, ZurZeit, FREILICH, ServusTV |
| F radical right / externally classified extreme-right spectrum | AUF1, Info-DIREKT, Unzensuriert, Heimatkurier, Der Status |

The A–F table is a research-planning matrix, not a persisted FSC political classification. Persisted Source-level political or radicality assignments still require two independent external sources that materially agree.

Politically unclassified/specialist digital candidates: Kronen Zeitung / krone.at, Heute / heute.at, ÖSTERREICH / oe24 / oe24.at, ZackZack, DOSSIER, Kobuk and Report24.

Specific identity rules:

- Existing print Sources are extended for Der Funke, Die Rote Fahne, Volksstimme, Der Standard, Falter, Kleine Zeitung, profil, Die Presse, Kurier, Salzburger Nachrichten, Die Furche, ZurZeit, FREILICH, Info-DIREKT, Kronen Zeitung, Heute and ÖSTERREICH / oe24.
- Existing broadcast Sources are extended for ORF Information, ProSiebenSat.1 PULS 4 Newsroom, ServusTV and AUF1.
- **MOMENT.at, eXXpress, Unzensuriert, Heimatkurier, Der Status, ZackZack, DOSSIER, Kobuk and Report24** are new born-digital Source identities.
- **WZ / Wiener Zeitung** is a new active digital Source with historic Wiener Zeitung continuity; it is not modeled as born-digital.
- Catalog placement for eXXpress, Unzensuriert, Heimatkurier and Der Status does not itself create a persisted political or radicality classification.
- Aggregators and distribution platforms are not editorial Sources.

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

## Switzerland (CH) — Digital

Digital is modeled as a **medium**. Existing print/broadcast Sources are extended rather than duplicated. Born-digital Sources use `digital_native`; digital continuations of former print brands use `other`.

The approved CH digital set contains 32 candidates: 23 in the A–F planning core and nine unclassified/specialist candidates. Of those, 10 create new Source identities and 22 extend existing Sources.

| Planning segment | Digital Sources |
| --- | --- |
| A radical/system-oppositional left | solidaritéS, Voix Populaire |
| B left/centre-left/left-liberal | Watson, WOZ, Tages-Anzeiger, Le Courrier, Le Temps, laRegione |
| C liberal/centre/reference | 20 Minuten / 20 Minutes, Nau.ch, blue News, SRF, RTS, Corriere del Ticino |
| D conservative/liberal-conservative | Neue Zürcher Zeitung, Luzerner Zeitung, St. Galler Tagblatt, Schweizerzeit |
| E right/right-conservative/right-libertarian | Die Weltwoche, SVP-Klartext, Kontrafunk |
| F radical right / externally classified extreme-right spectrum | Kla.TV, Schweizer Demokrat |

The A–F table is a research-planning matrix, not a persisted FSC political classification. A and F deliberately remain below the 3–5 target; B and C exceed it because multilingual relevance is not removed to make the matrix symmetrical.

Unclassified/specialist candidates: Republik, Infosperber, Inside Paradeplatz, Le Matin, Antithèse & Bon pour la tête, TicinOnline / tio.ch, Blick, RSI and RTR.

Specific identity rules:

- **20 Minuten / 20 Minutes is one Source with German- and French-language outlets** under a joint national editorial leadership.
- **TicinOnline / tio.ch remains a separate Source** and is not collapsed into 20 Minuten / 20 Minutes.
- **Le Matin** is a separate active digital continuation from **Le Matin Dimanche** and is not born-digital.
- **Antithèse & Bon pour la tête** is one merged Source, not two.
- **WIDERSPRUCH** is not counted as a digital outlet merely because selected texts appear online.
- Existing print/broadcast Sources are extended for solidaritéS, Voix Populaire, WOZ, Tages-Anzeiger, Le Courrier, Le Temps, laRegione, SRF, RTS, Corriere del Ticino, Neue Zürcher Zeitung, Luzerner Zeitung, St. Galler Tagblatt, Schweizerzeit, Die Weltwoche, SVP-Klartext, Kontrafunk, Kla.TV, Schweizer Demokrat, Blick, RSI and RTR.
- Heidi.news remains deferred pending a cleaner current editorial-dependency assessment relative to Le Temps.

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
- **Sky News Radio** is modeled as a radio outlet/service of the existing Sky News Source, not as a second independent Source.
- **Talk** is included as a current national radio/digital Source; the former linear TalkTV channel is not treated as a current television Source.
- Christian broadcasters may enter the catalog when news, politics or society are recurring editorial subjects. Christian identity is never automatically mapped to D or any other political segment.
- Local, regional and devolved broadcasters, including BBC Local Radio, STV and S4C, remain outside this national block for later GB regional/devolved review.
- Digital-native audiovisual outlets such as Novara Media are handled in the GB digital catalog rather than duplicated as broadcast Sources.

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
- **ABC News Radio** and **Fox News Radio** are modeled as radio outlets/services of the existing ABC News and Fox News Sources, not as independent Sources.
- **CBS News Radio** is excluded from the active core because the service ended on May 22, 2026.
- **C-SPAN/C-SPAN Radio** are deferred to an institutional/public-affairs primary-source block.
- **CNBC, Bloomberg and Fox Business** are deferred to a specialist economic/financial source block.
- Local network affiliates, regional public-media stations and local talk radio remain outside this national block for later US regional review.

No feed is activated by inclusion in this catalog.

## Switzerland (CH) — Regional broadcast

This compact block selects licensed regional television and local-radio Sources across the German-, French- and Italian-speaking media regions. It does not attempt a canton-by-canton quota.

The initial core contains 12 politically unclassified Sources: six television and six radio.

Television: TeleBärn, Tele M1, TVO, Léman Bleu, Canal 9/Kanal 9 and TeleTicino.

Radio: Radio Central, Radio Grischa, Radio Chablais, RadioFr. Fribourg/Freiburg, Radio Ticino and Radio BeO.

Specific identity rules:

- BAKOM concessions establish these as genuine regional/local broadcasters with regional-information duties, but do not imply political orientation.
- Shared ownership does not merge editorially independent regional stations. In particular, CH Media has stated that its licensed regional TV stations remain editorially independent.
- Canal 9/Kanal 9 is one bilingual Valais Source with French- and German-language outlets.
- RadioFr. Fribourg/Freiburg is one bilingual Fribourg Source with French- and German-language radio outlets.
- SRF, RTS, RSI and RTR are not duplicated in this regional catalog. Their regional output remains part of the already existing national language-region Sources.
- Remaining BAKOM-concessioned regional television and local radio providers remain available for later expansion; the core is deliberately multilingual and compact rather than quota-driven.
- No selected private regional Source currently has sufficient two-independent-source provenance for an A–F political placement.

No feed is activated by inclusion in this catalog.

## Great Britain (GB) — Regional/devolved broadcast

This compact block covers the three devolved nations and deliberately avoids expanding into every English ITV region or commercial local-radio brand.

The core contains six Sources:

- Public-service reference: BBC Scotland, BBC Cymru Wales and BBC Northern Ireland.
- Politically unclassified private television: STV News, ITV Cymru Wales and UTV.

Specific identity rules:

- BBC Scotland, BBC Cymru Wales and BBC Northern Ireland are three devolved cross-media Sources for FSC regional independence counting. Their television and nation-specific radio services are outlets.
- STV News is one Scottish Source despite STV's two licence areas; 2026 Ofcom-approved changes increase shared content while retaining bespoke regional sections.
- ITV Cymru Wales and UTV remain separate from national ITV News because they are dedicated devolved ITV newsrooms rather than the ITN-produced national newsroom.
- S4C is not duplicated as a news Source: Newyddion S4C is produced by BBC Cymru Wales. S4C's independently commissioned current-affairs output can be revisited separately.
- BBC ALBA is deferred because its joint BBC Scotland/MG ALBA structure requires explicit joint-source independence modeling.
- English ITV regional newsrooms and commercial local radio remain deferred to a later local/regional expansion.

No feed is activated by inclusion in this catalog.

## Great Britain (GB) — Digital

Digital is modeled as a **medium**. Existing national broadcast Sources are extended rather than duplicated. Born-digital Sources use `digital_native`; print-origin and digital-continuation Sources use `other`.

The GB digital candidate set contains 28 candidates: 23 in the A–F planning core and five unclassified/specialist candidates. Of those, 23 create new Source identities and five extend existing broadcast Sources.

| Planning segment | Digital Sources |
| --- | --- |
| A radical/system-oppositional left | Novara Media, The Canary, Morning Star, Socialist Worker |
| B left/centre-left/left-liberal | The Guardian, The Independent, openDemocracy, Byline Times, New Statesman |
| C liberal/centre/reference | BBC News, ITV News, Channel 4 News, Sky News, Financial Times, The Economist |
| D conservative/liberal-conservative | The Times, The Telegraph, The Spectator |
| E right/right-conservative/right-libertarian | GB News, UnHerd, The Critic, Spiked, Daily Mail |
| F radical right / externally classified extreme-right spectrum | explicit market gap |

The A–F table is a research-planning matrix, not a persisted FSC political classification. The F gap is deliberately left visible rather than filled with marginal activist or conspiracy sites that do not meet the core editorial-source threshold.

Unclassified/specialist candidates: Full Fact, PoliticsHome, The Conversation UK, Private Eye and Prospect.

Specific identity rules:

- BBC News, ITV News, Channel 4 News, Sky News and GB News extend their existing broadcast Sources.
- The Independent is a digital continuation of a former print newspaper and is not modeled as born-digital.
- Morning Star, Socialist Worker, The Guardian, Financial Times, The Economist, The Times, The Telegraph, The Spectator, The Critic, Daily Mail, Byline Times, New Statesman, Private Eye and Prospect are print/cross-format-origin Sources and use `publication_form=other`.
- Novara Media, The Canary, openDemocracy, UnHerd, Spiked, Full Fact, PoliticsHome and The Conversation UK use `digital_native`.
- The Canary is active at the catalog review date; reported financial-continuity risk does not itself change Source identity.

No feed is activated by inclusion in this catalog.

## United States (US) — Digital

Digital is modeled as a **medium**. Existing broadcast Sources are extended rather than duplicated. Born-digital Sources use `digital_native`; print-origin and cross-format Sources use `other`.

The approved US digital candidate set contains 32 candidates: 27 in the A–F research-planning core and five politically unclassified/specialist candidates. Of those, 23 create new Source identities and nine extend existing broadcast Sources.

| Planning segment | Digital Sources |
| --- | --- |
| A radical/system-oppositional left | Jacobin, Truthout, Common Dreams, Democracy Now! |
| B left/centre-left/left-liberal | NPR, CNN, HuffPost, Vox, The Intercept |
| C liberal/centre/reference | Axios, POLITICO, Semafor, ABC News, CBS News, NBC News |
| D conservative/liberal-conservative | The Wall Street Journal, The Dispatch, National Review, The Bulwark |
| E right/right-conservative/right-libertarian | Reason, The Daily Wire, Washington Examiner, The Federalist, Fox News |
| F radical right / externally classified far-right spectrum | Breitbart, The Gateway Pundit, One America News |

The A–F table is a research-planning matrix, not a persisted FSC political classification. Persisted political or radicality assignments still require two independent external sources that materially agree.

Politically unclassified/specialist digital candidates: ProPublica, The Hill, NOTUS, The 19th and Newsmax.

Specific identity rules:

- Democracy Now!, NPR, CNN, ABC News, CBS News, NBC News, Fox News, One America News and Newsmax extend their existing national broadcast Sources.
- Print-origin or established cross-format publications such as Jacobin, POLITICO, The Wall Street Journal, National Review, Reason, Washington Examiner and The Hill use `publication_form=other`, not `digital_native`.
- Born-digital newsrooms such as Truthout, Common Dreams, HuffPost, Vox, The Intercept, Axios, Semafor, The Dispatch, The Bulwark, The Daily Wire, The Federalist, Breitbart, The Gateway Pundit, ProPublica, NOTUS and The 19th use `digital_native`.
- Newsmax remains politically unclassified in FSC because the existing external evidence disagrees on radicality; digital presence does not change that rule.
- Aggregators, social platforms and carrier/distribution services are not editorial Sources.

No feed is activated by inclusion in this catalog.

## United States (US) — Regional broadcast

This block is deliberately representative rather than exhaustive. The US local-affiliate system contains hundreds of independently operated newsrooms, so FSC uses a compact state-/major-metro core and leaves the affiliate universe for a later local layer.

The initial core contains 10 politically unclassified regional Sources:

WNYC / Gothamist Newsroom, NJ Spotlight News, WHYY News, WBEZ Chicago, WABE News, KUT News, KQED News, LAist, Spectrum News NY1 and Spectrum News 1 North Carolina.

Specific identity rules:

- NPR/PBS membership, affiliation or programme carriage does not merge a regional newsroom into the national NPR or PBS NewsHour Sources.
- **WNYC and Gothamist** are outlets of one integrated New York Public Radio newsroom rather than two independent Sources.
- **KUT News** is the Source for KUT 90.5 and the statewide Texas Standard programme. Texas Standard's collaboration with KERA, Houston Public Media and Texas Public Radio does not create four independent Sources.
- **Spectrum News NY1** and **Spectrum News 1 North Carolina** remain separate regional Sources despite common Charter/Spectrum ownership because they operate distinct geographic newsrooms.
- ABC, CBS, NBC and Fox local affiliates are not collapsed into four network Sources. Their large universe of individual local newsrooms is deferred to a later local-affiliate layer.
- Sinclair ownership and shared content infrastructure likewise do not create one national/regional Sinclair newsroom; station-level identity requires later review.
- GBH/NEPM is deferred while its 2026 merger/integration settles into a stable editorial structure.
- Spanish-language local affiliates are deferred for a deliberate multilingual local-affiliate expansion rather than sampled inconsistently here.
- All ten selected Sources remain politically unclassified. Public-media status is not used as a substitute for political classification.

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
14. Austria regional broadcast candidate core (state/multi-state level; local/community broadcast separate)
15. Switzerland regional broadcast candidate core (compact multilingual licensed regional set)
16. Great Britain regional/devolved broadcast candidate core (devolved nations; local English regions separate)
17. United States regional broadcast candidate core (representative state/major-metro set; local affiliates separate)
18. Agency / Content Supplier core (national and global agencies plus broadcast supplier; cross-media radio services deduplicated)
19. Germany digital candidate core (digital as medium; cross-media Sources reused)
20. Austria digital candidate core (digital as medium; cross-media Sources reused)
21. Switzerland digital candidate core (multilingual digital set; cross-media Sources reused)
22. Great Britain digital candidate core (digital as medium; cross-media Sources reused)
23. United States digital candidate core (digital as medium; cross-media Sources reused)

Foreign-language media are part of the current product scope. Catalog completeness is defined by comparative value and provenance, not by world or country coverage.

## Activation rule

A catalog entry may only receive active production feeds after joint source review. Building the catalog, metadata model, provenance records and technical feed validation does not itself authorize activation.
