# ADR 0025: Broad-mission foundations remain NGO

## Status

Accepted.

## Context

Germany has several political foundations and large operational foundations that
publish policy analysis and studies but whose institutional missions are broader
than think-tank work alone. Their activities can include political or civic
education, scholarship and talent support, international cooperation, culture,
research funding, projects and public-interest programmes.

Treating the complete institution as `THINK_TANK` would make every newly
ingested item default to `confirmation_role=expert_analysis`, including
education, institutional, campaign-like or position content that is not expert
analysis.

Article-level `confirmation_role` already provides the correct place to
distinguish individual analytical publications from other institutional output.

## Decision

Broad-mission political and operational foundations are `NGO` Sources when
their overall institutional purpose is mission-driven civil-society work and
think-tank/policy-analysis activity is only one part of that broader mission.

For the German core this includes:

- Konrad-Adenauer-Stiftung;
- Friedrich-Ebert-Stiftung;
- Heinrich-Böll-Stiftung;
- Friedrich-Naumann-Stiftung für die Freiheit;
- Rosa-Luxemburg-Stiftung;
- Hanns-Seidel-Stiftung;
- Desiderius-Erasmus-Stiftung;
- Bertelsmann Stiftung.

These institutions receive no FSC political-orientation classification merely
from their identity, name, legal form or institutional context.

The dedicated `THINK_TANK` type remains reserved for institutions whose
primary institutional function is policy analysis, strategic advice, policy
development or public-policy debate.

## Confirmation semantics

New items from these foundation Sources use the normal `NGO` default:

`confirmation_role=advocacy`.

This remains only a default. A concrete publication can be assigned:

- `expert_analysis` when it is a substantive analytical study;
- `primary_evidence` when it directly publishes the institution's own data or
  administrative facts;
- `editorial` when a genuinely editorial item warrants that role.

Only the article-level role determines independent-confirmation eligibility.

## Source identity

The foundation itself is the Source. Internal academies, education programmes,
research units, scholarship programmes, international offices and project
brands are not automatic separate Sources.

If a legally or institutionally distinct entity later becomes independently
relevant, it can be reviewed separately under the normal Source identity rules.

## Consequences

The German NGO core expands from 22 to 30 Sources.

The German THINK_TANK core can remain focused on institutions whose primary
function is policy analysis rather than broad foundation activity.

No additional SourceType such as `POLITICAL_FOUNDATION` is introduced.
