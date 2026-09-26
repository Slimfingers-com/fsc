# ADR 0024: Academic and think-tank source boundary

## Status

Accepted.

## Context

FSC distinguishes `ACADEMIC` from `THINK_TANK`, but Germany has several
research institutes that both conduct peer-oriented scientific research and
advise politics and the public. Examples include ifo, DIW Berlin, ZEW, RWI,
IfW Kiel and WZB.

Classifying every policy-relevant research institute as a think tank would
collapse a meaningful institutional distinction. At the same time, using
`ACADEMIC` only for universities would make the type too narrow and exclude
major non-university research organizations whose primary purpose is scientific
research.

Article-level `confirmation_role` already determines whether a concrete item
counts as independent expert confirmation. The SourceType therefore describes
the institution, not the evidentiary role of every item it publishes.

## Decision

Use the **primary institutional function** as the boundary.

`ACADEMIC` includes institutions whose primary institutional function is
scientific research, including:

- universities and university medical institutions;
- academies of sciences;
- non-university research institutes and research centers;
- research organizations whose substantive institutional purpose is scientific
  research.

Policy advice, public communication and knowledge transfer do not turn a
research institution into a think tank when they are based on and secondary to
its primary scientific research function.

`THINK_TANK` is reserved for institutions whose primary institutional
function is policy analysis, strategic advice, policy development or public
policy debate rather than scientific research as such.

Accordingly, ifo, DIW Berlin, ZEW, RWI, IfW Kiel and WZB are `ACADEMIC` in
the German source catalog. Institutions such as SWP and DGAP belong to the
`THINK_TANK` category when that catalog is implemented.

## Source identity

The institutional unit is the Source.

Universities are represented at university level by default; faculties,
departments, chairs and institutes are not automatically separate Sources.

Large research organizations such as the Max Planck Society and Fraunhofer
Society are represented as organization-level Sources in the compact core.
Individual institutes can be added later when their independently relevant
institutional voice warrants a separate Source.

Independent large-scale research centers such as DLR, Forschungszentrum
Jülich, DKFZ or the Max Delbrück Center remain separate Sources even when they
belong to a broader research association. Membership in a research association
is not itself a reason to collapse Source identities.

## Confirmation semantics

New articles from `ACADEMIC` and `THINK_TANK` Sources default to
`confirmation_role=expert_analysis`.

This remains only a default. A concrete item may instead be:

- `primary_evidence` for the institution's own administrative data, original
  measurements or directly published study data;
- `advocacy` for an institutional position or campaign-like statement;
- `editorial` when a genuinely editorial item justifies that role.

Consensus and coverage therefore continue to use the shared article-level
confirmation eligibility function. The SourceType itself does not guarantee
independent confirmation.

## Consequences

FSC can represent the German scientific research landscape without equating
policy-relevant research with think-tank activity.

No additional SourceType such as `RESEARCH_INSTITUTE` is introduced.

The distinction remains organizational and does not create separate consensus
or coverage logic.
