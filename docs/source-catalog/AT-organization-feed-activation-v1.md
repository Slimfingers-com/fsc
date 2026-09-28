# Austria organization feed activation review v1

Review date: 2026-09-28

## Scope

This review applies ADR 0027 to the existing Austrian `ACADEMIC`,
`THINK_TANK`, `COMPANY`, `NGO` and `INTEREST_GROUP` catalogs.

The German activation rules remain unchanged:

- concrete content channels are reviewed, not whole Sources;
- `feed_class` and `activation_tier` remain catalog/review metadata only;
- press/news channels are primary evidence for what an institution states;
- interest-bound research from COMPANY, NGO and INTEREST_GROUP Sources remains
  `advocacy` and does not create independent confirmation;
- mixed or provenance-ambiguous feeds remain inactive.

## Tier 1: activated

### SOS Mitmensch — Aktuelles

- URL: `https://www.sosmitmensch.at/backend/rss/rss2?channel=aktuelles`
- class: `news`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- verification: direct parsing returned RSS 2.0 with current entries.
- rationale: highly relevant to Austrian migration, anti-discrimination and
  democratic-policy coverage. The feed is evidence for SOS Mitmensch's own
  statements and actions, not independent confirmation.

### epicenter.works — Dokumente

- URL: `https://epicenter.works/rss/dokumente.feed.xml`
- class: `position_statement`
- role: `advocacy`
- priority: 1
- interval: 60 minutes
- verification: epicenter.works explicitly documents a separate documents RSS
  containing analyses, open letters, legislative submissions and position
  papers; direct parsing returned RSS 2.0.
- rationale: digital-rights and technology-policy material is highly relevant,
  while the conservative advocacy role is valid across the channel.

### Österreichische Ärztekammer — Presseinformationen

- URL: the official Liferay RSS endpoint exposed by the Ärztekammer press page.
- class: `press_release`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- verification: direct parsing returned RSS 2.0 with current press entries.
- rationale: relevant primary evidence for health-policy positions and
  institutional statements.

## Tier 2: verified but initially disabled

### Universität Wien — Aktuelles

- URL: `https://www.univie.ac.at/aktuelles/aktuelles-rss/feed.xml`
- class: `news`
- role: `primary_evidence`
- status: inactive
- rationale: technically clean official RSS, but broad institutional news is
  less central to initial FSC policy/news coverage.

### Universität Innsbruck — Pressemitteilungen

- URL: `https://www.uibk.ac.at/newsroom/pressemitteilungen.rss`
- class: `press_release`
- role: `primary_evidence`
- status: inactive
- rationale: clean official press feed, but lower priority for the initial
  Austrian evidence set.

## Reviewed but not configured

### WIFO

WIFO exposes separate RSS endpoints for news, publications and events. The
publication feed is technically valid but combines studies, working papers,
monthly reports, press releases and cooperative/external publication contexts.
Assigning the entire feed `expert_analysis` would be too coarse, while treating
it as one generic news class would lose the distinction the feed is supposed to
provide. It remains unconfigured until a narrower research-only channel or
entry-level routing exists.

### Momentum Institut

The general RSS feed mixes institute material with content whose canonical link
can point to MOMENT.at. Activating it directly under the Momentum Institut
Source would blur source identity/provenance.

### Agenda Austria, Austrian Economics Center and ÖGfE

Their general feeds are technically parseable but mix analysis, commentary,
interviews, events or other site content. No single narrow research role is
assigned in this pass.

### Austrian companies

No company channel discovered in this pass met both requirements of a stable,
official feed endpoint and sufficiently narrow content semantics. No feed URL is
guessed.

### Other NGOs and interest groups

Several sites expose generic WordPress or service feeds. They remain
unconfigured when the channel is broad, mixed or technically ambiguous. Clean
dedicated channels can be added later without changing the activation model.

## Runtime consequence

Only the three Tier-1 feeds above become active ingestion candidates. The two
academic Tier-2 feeds are retained as reviewed metadata with `active=false`.
No Austrian THINK_TANK or COMPANY feed is activated merely because the parent
SourceType would supply a default confirmation role.
