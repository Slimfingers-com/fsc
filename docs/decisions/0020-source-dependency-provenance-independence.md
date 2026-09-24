# ADR 0020: Source Dependency and Article Provenance Independence

## Status

Accepted

## Context

FSC must distinguish legal ownership, editorial independence and concrete content provenance. Sources under common ownership can operate independent newsrooms, while separately branded Sources can publish material supplied by the same upstream newsroom or agency.

Counting `Source.ownership` as the independence key therefore both undercounts genuinely independent sibling newsrooms and overcounts syndicated, republished or supplied content.

## Decision

FSC models two complementary dependency layers:

- `SourceRelation` stores structural relationships between Sources: `editorial_parent`, `shared_newsroom`, `content_supplier`, `syndication_partner` and `joint_editorial_operation`.
- `ArticleProvenance` stores article-specific dependencies: `supplied_by`, `syndicated_from`, `republished_from` and `co_produced_with`.

Only `editorial_parent`, `shared_newsroom` and `joint_editorial_operation` collapse Sources statically for independence counting. A `content_supplier` or `syndication_partner` relationship documents capability or structure but does not make every article dependent.

Only verified `ArticleProvenance` affects Consensus and Coverage independence. Unverified observations remain audit data without changing counts.

Article provenance is followed transitively through `upstream_article_id`. For example, if a station article is supplied by a radio news service and that upstream article is itself republished from an agency, the final dependency reaches the agency rather than stopping at the intermediary.

When an article depends on multiple upstream Sources, including `co_produced_with`, FSC uses a conservative dependency-component rule. Within the story analysis context, all article dependency sets that overlap are merged transitively into one component. Therefore an X-only article, a jointly produced X+Y article and a Y-only article count as one independent content component, not three or two.

`co_produced_with` includes both the publishing Source and the declared upstream Source in the article dependency set. For `supplied_by`, `syndicated_from` and `republished_from`, the downstream publisher is not counted as an additional independent origin for that article.

The Source-level structural graph and the article-level provenance graph are both time-aware through the article analysis date for dated Source relations.

Consensus and Coverage processing identities include the applicable Source relations and verified recursive Article provenance. Their configuration versions are incremented whenever independence semantics change so previously persisted analysis generations become stale.

## Consequences

Ownership remains useful descriptive source metadata but is not an independence key.

Two outlets with the same owner can count independently when they have distinct newsrooms and no collapsing Source relation applies.

Two differently branded outlets do not count as independent confirmation when verified article provenance shows that they share the same upstream content origin.

The conservative co-production rule can undercount some genuinely independent contributions, but it prevents FSC from overstating corroboration. This is an intentional tradeoff.

Static supplier relations alone never imply that all downstream content is copied. Article-specific provenance is required to collapse supplier-dependent content.

Agency and content-supplier Sources can now be cataloged without treating every consumer outlet that uses them as automatically dependent.
