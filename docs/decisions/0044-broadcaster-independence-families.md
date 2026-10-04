# ADR 0044: Broadcaster independence families

## Status

Accepted

## Context

FSC represents regional broadcaster units as separate Sources because they have
distinct feeds, regional scope and presentation identity. ADR 0020 separately
requires FSC not to overstate independent corroboration.

Production now contains stories in which multiple regional units of the same
broadcaster appear together. Counting those units as independent confirmations
can overstate consensus even though the Sources must remain separate.

## Decision

BBC News plus BBC Scotland, BBC Cymru Wales and BBC Northern Ireland form one
static independence component.

ORF Information plus the nine ORF Landesstudio Sources form one static
independence component.

The relation kind is `editorial_parent`. This expresses an organizational
editorial family without asserting that the regional Sources share one physical
newsroom. It is used only by the existing ADR 0020 independence resolver.

Sources, feeds, regional metadata, search and presentation remain separate.

ARD Landesrundfunkanstalten are not collapsed by this decision. BR, WDR, NDR,
MDR and other legally/editorially distinct broadcasters remain separate unless
future evidence justifies a specific SourceRelation.

## Consequences

Consensus and Coverage can no longer count two BBC regional Sources or two ORF
regional Sources as independent corroboration merely because they are distinct
FSC Source records.

Article-specific provenance remains complementary and can still collapse
otherwise separate Sources when verified.
