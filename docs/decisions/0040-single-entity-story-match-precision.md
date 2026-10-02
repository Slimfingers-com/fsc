# ADR 0040: Conservative single-entity story matching

Status: Accepted
Date: 2026-10-02

## Context

Production validation of ADR 0039 exposed a same-language precision gap.
The rule-based clusterer could accept a candidate when only one canonical
Entity was shared and title Jaccard similarity was as low as 0.15.

Because the final weighted score also includes Entity and Topic overlap,
one broad or recurring Entity could push semantically different articles
above the global 0.45 similarity floor. Observed examples included distinct
election stories about the same candidate being merged into one Story.

Production inspection also showed that Entity frequency is not a reliable
separator: both valid continuing coverage and false merges may involve
frequently occurring Entities. Semantic embeddings were absent for the
observed weak single-Entity matches, so they cannot be required without
turning an optional recall aid into a runtime dependency.

## Decision

The local rule-based Story clustering provider is advanced to version 4.

For same-language matches supported by exactly one or more shared Entities,
the entity-plus-title acceptance path now requires title Jaccard similarity
of at least 0.30. The threshold is explicit configuration and is part of the
processing configuration identity.

The independent acceptance paths remain unchanged:
- strong same-language title similarity at 0.50 or above;
- at least two shared canonical Entities;
- compatible semantic similarity at the configured semantic threshold;
- ADR 0039 cross-language rules.

Therefore a weak-title single-Entity match without semantic support is
rejected, while strong semantic evidence or multiple canonical Entities can
still recover recall.

The default threshold is exposed as
`STORY_CLUSTERING_SINGLE_ENTITY_TITLE_SIMILARITY_THRESHOLD=0.30`.

## Consequences

The change deliberately favors precision over recall for weak same-language
single-Entity evidence. Some continuing coverage with very low lexical overlap
may temporarily remain in separate Stories when no semantic embedding exists.

No embedding service becomes mandatory. Multi-Entity and semantic matching
continue to work exactly as independent evidence paths.

Provider version 4 and the changed configuration identity force deterministic
reprocessing of eligible articles. Historical StoryArticle rows retain the
previous match evidence, so the transition remains auditable.

This ADR supersedes ADR 0039 only where it states that same-language matching
rules remain unchanged. Cross-language acceptance and concurrency semantics
from ADR 0039 are unaffected.
