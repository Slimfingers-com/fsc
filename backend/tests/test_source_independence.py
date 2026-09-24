from datetime import UTC, date, datetime
from uuid import uuid4

from app.enums.source_dependency import (
    ArticleProvenanceDetectionMethod,
    ArticleProvenanceKind,
    SourceRelationKind,
)
from app.models.source_dependency import ArticleProvenance, SourceRelation
from app.services.source_independence import SourceIndependenceResolver


def relation(
    left,
    right,
    kind,
    *,
    valid_from=None,
    valid_to=None,
):
    return SourceRelation(
        id=uuid4(),
        source_id=left,
        related_source_id=right,
        relation_kind=kind,
        valid_from=valid_from,
        valid_to=valid_to,
    )


def provenance(article_id, upstream_source_id):
    return ArticleProvenance(
        id=uuid4(),
        article_id=article_id,
        upstream_source_id=upstream_source_id,
        relation_kind=ArticleProvenanceKind.SUPPLIED_BY,
        confidence=1.0,
        detection_method=ArticleProvenanceDetectionMethod.MANUAL,
        verified=True,
    )


def test_shared_editorial_relations_are_transitive():
    first = uuid4()
    second = uuid4()
    third = uuid4()
    resolver = SourceIndependenceResolver(
        relations=(
            relation(
                first,
                second,
                SourceRelationKind.SHARED_NEWSROOM,
            ),
            relation(
                second,
                third,
                SourceRelationKind.EDITORIAL_PARENT,
            ),
        ),
        provenance=(),
    )

    keys = {
        resolver.source_key(first),
        resolver.source_key(second),
        resolver.source_key(third),
    }
    assert len(keys) == 1


def test_static_content_supplier_relation_does_not_collapse_sources():
    first = uuid4()
    second = uuid4()
    resolver = SourceIndependenceResolver(
        relations=(
            relation(
                first,
                second,
                SourceRelationKind.CONTENT_SUPPLIER,
            ),
        ),
        provenance=(),
    )

    assert resolver.source_key(first) != resolver.source_key(second)


def test_verified_article_provenance_collapses_to_upstream_source():
    downstream = uuid4()
    upstream = uuid4()
    article_id = uuid4()
    resolver = SourceIndependenceResolver(
        relations=(),
        provenance=(
            provenance(article_id, upstream),
        ),
    )

    assert resolver.article_key(
        article_id=article_id,
        source_id=downstream,
    ) == resolver.source_key(upstream)


def test_relation_validity_is_evaluated_at_article_date():
    first = uuid4()
    second = uuid4()
    resolver = SourceIndependenceResolver(
        relations=(
            relation(
                first,
                second,
                SourceRelationKind.SHARED_NEWSROOM,
                valid_from=date(2026, 1, 1),
                valid_to=date(2026, 12, 31),
            ),
        ),
        provenance=(),
    )

    inside = datetime(2026, 9, 24, tzinfo=UTC)
    outside = datetime(2027, 1, 1, tzinfo=UTC)
    assert resolver.source_key(first, at=inside) == resolver.source_key(
        second,
        at=inside,
    )
    assert resolver.source_key(first, at=outside) != resolver.source_key(
        second,
        at=outside,
    )


def test_dated_relation_does_not_apply_when_article_date_is_unknown():
    first = uuid4()
    second = uuid4()
    resolver = SourceIndependenceResolver(
        relations=(
            relation(
                first,
                second,
                SourceRelationKind.JOINT_EDITORIAL_OPERATION,
                valid_from=date(2026, 1, 1),
            ),
        ),
        provenance=(),
    )

    assert resolver.source_key(first) != resolver.source_key(second)


def test_co_produced_article_bridges_dependency_components_conservatively():
    first_source = uuid4()
    second_source = uuid4()
    first_article = uuid4()
    joint_article = uuid4()
    second_article = uuid4()

    joint_provenance = ArticleProvenance(
        id=uuid4(),
        article_id=joint_article,
        upstream_source_id=second_source,
        relation_kind=ArticleProvenanceKind.CO_PRODUCED_WITH,
        confidence=1.0,
        detection_method=ArticleProvenanceDetectionMethod.MANUAL,
        verified=True,
    )
    resolver = SourceIndependenceResolver(
        relations=(),
        provenance=(joint_provenance,),
    )

    keys = resolver.article_component_keys(
        articles=(
            (first_article, first_source, None),
            (joint_article, first_source, None),
            (second_article, second_source, None),
        )
    )

    assert len(set(keys.values())) == 1


def test_article_provenance_follows_upstream_article_transitively():
    downstream_source = uuid4()
    intermediary_source = uuid4()
    root_source = uuid4()
    downstream_article = uuid4()
    intermediary_article = uuid4()

    resolver = SourceIndependenceResolver(
        relations=(),
        provenance=(
            ArticleProvenance(
                id=uuid4(),
                article_id=downstream_article,
                upstream_source_id=intermediary_source,
                upstream_article_id=intermediary_article,
                relation_kind=ArticleProvenanceKind.SUPPLIED_BY,
                confidence=1.0,
                detection_method=ArticleProvenanceDetectionMethod.MANUAL,
                verified=True,
            ),
            ArticleProvenance(
                id=uuid4(),
                article_id=intermediary_article,
                upstream_source_id=root_source,
                relation_kind=ArticleProvenanceKind.REPUBLISHED_FROM,
                confidence=1.0,
                detection_method=ArticleProvenanceDetectionMethod.MANUAL,
                verified=True,
            ),
        ),
    )

    assert resolver.article_dependency_keys(
        article_id=downstream_article,
        source_id=downstream_source,
    ) == frozenset({resolver.source_key(root_source)})
    assert resolver.article_key(
        article_id=downstream_article,
        source_id=downstream_source,
    ) == resolver.source_key(root_source)
