# United Kingdom organization feed activation review v1

Review date: 2026-09-28

## Scope

This review applies ADR 0027 to the United Kingdom `ACADEMIC`,
`THINK_TANK`, `COMPANY`, `NGO` and `INTEREST_GROUP` catalogs.

The conservative rules used for Germany, Austria and Switzerland continue to
apply. Feed activation is channel-specific. Research or commentary from an
interest-bound Source never becomes independent confirmation merely because it
is analytical.

## Tier 1: activated

### University of Cambridge — University news

- URL: `https://www.cam.ac.uk/news-feed-generator.rss`
- class: `news`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- Cambridge documents its news-feed generator as an RSS source for the most
  recent University news items.
- direct parsing returned valid RSS 2.0 with ten current entries.
- the channel mixes research announcements and institutional news, so it is
  deliberately not classified as `research_publication`.

### Chatham House — Expert comments

- URL: `https://www.chathamhouse.org/path/83/feed.xml`
- class: `research_publication`
- role: `expert_analysis`
- priority: 1
- interval: 60 minutes
- Chatham House lists a dedicated Expert comments RSS feed separate from its
  general What's new, Events and News releases feeds.
- direct parsing returned valid RSS 2.0 with current analytical commentary.
- ADR 0027 defines `research_publication` broadly enough to include a
  consistently analytical publication channel; the generic Chatham House feed
  is not used.

### Royal United Services Institute (RUSI) — Latest commentary

- URL: `https://www.rusi.org/rss/latest-commentary.xml`
- class: `research_publication`
- role: `expert_analysis`
- priority: 1
- interval: 60 minutes
- RUSI publishes dedicated RSS endpoints for commentary, publications, events
  and general updates.
- direct parsing of the commentary feed returned valid RSS 2.0 and current
  analytical articles.
- the broader `latest-publications.xml` endpoint is not used because it also
  contains newsbriefs, event recordings and podcasts.

### British Chambers of Commerce — News

- URL: `https://www.britishchambers.org.uk/feed/`
- class: `news`
- role: `primary_evidence`
- priority: 1
- interval: 60 minutes
- direct parsing returned valid RSS 2.0 with current BCC news, economic
  reactions, research announcements and institutional commentary.
- `primary_evidence` records what the interest group states without creating
  independent confirmation.

## Tier 2: verified but initially disabled

### GSK — Media releases

- URL: `https://www.gsk.com/en-gb/media/rss/`
- class: `press_release`
- role: `primary_evidence`
- priority: 2
- interval: 120 minutes
- status: inactive
- GSK's official RSS service exposes a technically valid media-release feed.
- direct parsing returned RSS 2.0, but the endpoint currently exposes a very
  large historical archive rather than only a small recent window.
- it is retained as a verified candidate but left inactive to avoid an
  unnecessarily large first ingestion.

## Reviewed but not configured

### NIESR

`https://niesr.ac.uk/feed` is technically valid and recent entries are
analytical blog posts, but it is the site's broad root feed rather than a
narrow research-series endpoint. It remains unconfigured until a stable
publication channel is verified.

### Resolution Foundation

The general WordPress feed is technically valid but current entries are
`/comment/` articles. It is not treated as a research-publication feed.

### IPPR, IEA and other think tanks

IPPR's general RSS mixes jobs, profiles, media releases and articles. IEA's
general feed mixes briefings, opinion pieces and book reviews. Similar generic
feeds are not activated where one existing feed class does not cleanly describe
the channel.

### Chatham House general and news-release feeds

The general What's new feed mixes events, news and publications. The separate
news-release feed is technically clean but is lower-value for FSC than the
dedicated expert-comment channel, so it is not activated in the initial pass.

### RUSI general publications feed

The `latest-publications.xml` feed includes commentary but also newsbriefs,
event recordings and podcasts. The dedicated commentary feed is used instead.

### NGOs

Privacy International, Open Rights Group and Good Law Project expose technically
valid broad feeds, but those feeds mix advocacy, reports, campaigns, long-form
analysis and other formats. They remain unconfigured rather than forcing one
feed class onto materially different content.

### Other interest groups

No additional reviewed interest-group endpoint in this pass met both the
stable-endpoint and sufficiently coherent-content requirements.

## Source identity and role semantics

The Source remains the institutional unit from the existing catalog. Feed
activation does not create new Sources for programmes, publications or
distribution channels.

`ACADEMIC` and `THINK_TANK` channels may use `expert_analysis` only where
the concrete channel is consistently analytical. `COMPANY`, `NGO` and
`INTEREST_GROUP` research remains interest-bound and therefore cannot create
independent confirmation merely because the material resembles research.
