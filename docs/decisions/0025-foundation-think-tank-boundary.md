# ADR 0025: Broad-mission political education institutions remain NGO

## Status

Accepted.

## Context

FSC needs to classify institutions that publish policy analysis but whose
overall institutional missions are broader than think-tank work alone.

Germany has several political and operational foundations whose activities can
include political or civic education, scholarship and talent support,
international cooperation, culture, research funding, projects and
public-interest programmes.

Austria has a comparable but institutionally different form: party academies
and political education institutes such as Campus Tivoli, Karl-Renner-Institut,
Freiheitliches Bildungsinstitut, FREDA and NEOS Lab. They also combine
education, training, events, participation, institutional work and in some
cases policy analysis.

Treating the complete institution as `THINK_TANK` would make every newly
ingested item default to `confirmation_role=expert_analysis`, including
education, institutional, event, campaign-like or position content that is not
expert analysis.

Article-level `confirmation_role` already provides the correct place to
distinguish individual analytical publications from other institutional output.

## Decision

Broad-mission political education institutions are `NGO` Sources when their
overall institutional purpose is mission-driven civic or political education
and think-tank/policy-analysis activity is only one part of that broader mission.

This rule applies regardless of whether the institution is legally organized
as a foundation, association, academy or another non-profit form.

For the German core this includes:

- Konrad-Adenauer-Stiftung;
- Friedrich-Ebert-Stiftung;
- Heinrich-Böll-Stiftung;
- Friedrich-Naumann-Stiftung für die Freiheit;
- Rosa-Luxemburg-Stiftung;
- Hanns-Seidel-Stiftung;
- Desiderius-Erasmus-Stiftung;
- Bertelsmann Stiftung.

For the Austrian core this includes:

- Campus Tivoli – Akademie der ÖVP;
- Karl-Renner-Institut;
- Freiheitliches Bildungsinstitut;
- FREDA – DIE AKADEMIE;
- NEOS Lab – Das liberale Forum.

These institutions receive no FSC political-orientation classification merely
from their identity, name, legal form, party proximity or institutional
context.

The dedicated `THINK_TANK` type remains reserved for institutions whose
primary institutional function is policy analysis, strategic advice, policy
development or public-policy debate.

## Confirmation semantics

New items from these NGO Sources use the normal `NGO` default:

`confirmation_role=advocacy`.

This remains only a default. A concrete publication can be assigned:

- `expert_analysis` when it is a substantive analytical study;
- `primary_evidence` when it directly publishes the institution's own data or
  administrative facts;
- `editorial` when a genuinely editorial item warrants that role.

Only the article-level role determines independent-confirmation eligibility.

## Source identity

The institution itself is the Source. Internal academies, education programmes,
research units, scholarship programmes, international offices, event series and
project brands are not automatic separate Sources.

If a legally or institutionally distinct entity later becomes independently
relevant, it can be reviewed separately under the normal Source identity rules.

## Consequences

The German NGO core remains at 30 Sources.

The Austrian NGO core includes the five national political education
institutions rather than placing them in the think-tank catalog.

German and Austrian THINK_TANK catalogs remain focused on institutions whose
primary function is policy analysis rather than broad political education.

No additional SourceType such as `POLITICAL_FOUNDATION` or
`POLITICAL_EDUCATION_INSTITUTE` is introduced.
