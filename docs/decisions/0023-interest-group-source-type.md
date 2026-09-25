# ADR 0023: Interest groups are a distinct source type

## Status

Accepted.

## Context

FSC already distinguishes editorial media, agencies, primary sources, NGOs,
companies, academic institutions, think tanks and signal sources. The source
catalog also needs institutional voices such as trade unions, employer and
industry associations, professional associations and comparable organized
interest representation.

Putting these organizations into `COMPANY` would misrepresent their
institutional identity. Treating all of them as `NGO` would make the NGO type
too broad and obscure the difference between civil-society advocacy
organizations and membership-based interest representation.

Article-level `confirmation_role` already answers the separate question of
how a concrete item contributes to confirmation. Source type must therefore
describe what the source *is*, not whether every item it publishes is advocacy,
analysis or evidence.

## Decision

Add `INTEREST_GROUP` to `SourceType`.

Use it for organized non-state interest representation whose institutional
purpose is primarily to represent member or sector interests, including:

- trade unions and union confederations;
- employer, business and industry associations;
- professional and sector associations;
- comparable membership-based lobbying or interest organizations.

Keep `NGO` for civil-society organizations whose primary identity is
mission-driven public-interest, rights, campaign, watchdog, humanitarian,
environmental or similar non-member-sector advocacy.

Keep `COMPANY` for commercial companies and corporate groups.

Keep `THINK_TANK` for organizations whose primary institutional function is
research and policy analysis rather than representing a member constituency.

A hybrid organization's primary institutional function determines its
`SourceType`; labels used in self-description alone do not control the type.

## Confirmation semantics

New articles from `INTEREST_GROUP` sources default to
`confirmation_role=advocacy`.

This is only a default. The role remains article-specific and may be overridden
when the content warrants it. For example:

- a position paper can remain `advocacy`;
- an independently reasoned analytical publication can be
  `expert_analysis`;
- publication of the organization's own membership survey or official figures
  can be `primary_evidence`;
- a genuinely editorial item can be `editorial` when justified.

Only `editorial` and `expert_analysis` count as independent confirmation.
The source type itself does not grant or deny independent-confirmation status.

## Consequences

The source catalog can represent DGB, BDI, Bitkom and comparable organizations
without conflating them with companies or classic NGOs.

Consensus and coverage require no source-type-specific exception: they continue
to consume the shared article-level confirmation eligibility function.

Existing sources and articles are unchanged. The database enum gains one value;
no backfill is required.
