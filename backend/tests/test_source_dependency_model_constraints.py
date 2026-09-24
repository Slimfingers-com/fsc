from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.source_dependency import (
    ArticleProvenanceDetectionMethod,
    ArticleProvenanceKind,
    SourceRelationKind,
)
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.models.source_dependency import ArticleProvenance, SourceRelation
from app.repositories.source_dependency import SourceDependencyRepository


def make_source(db, name: str) -> Source:
    slug = name.lower().replace(" ", "-")
    source = Source(
        name=name,
        normalized_name=name.casefold(),
        slug=f"{slug}-{uuid4().hex[:8]}",
        url=f"https://{slug}.example.com",
        source_type=SourceType.NEWS,
    )
    db.add(source)
    db.flush()
    return source


def make_article(db, source: Source, label: str) -> Article:
    feed = Feed(
        source=source,
        name=f"Feed {label}",
        url=f"https://{source.slug}.example.com/{label}.xml",
    )
    article = Article(
        feed=feed,
        identity_type=ArticleIdentityType.DERIVED,
        identity_key=uuid4().hex * 2,
        title=label,
    )
    db.add(article)
    db.flush()
    return article


def test_source_relation_rejects_self_relation(db):
    source = make_source(db, "Self Relation")
    db.add(
        SourceRelation(
            source_id=source.id,
            related_source_id=source.id,
            relation_kind=SourceRelationKind.SHARED_NEWSROOM,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_source_relation_rejects_invalid_kind(db):
    first = make_source(db, "Relation First")
    second = make_source(db, "Relation Second")
    db.add(
        SourceRelation(
            source_id=first.id,
            related_source_id=second.id,
            relation_kind="invalid",
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_source_relation_rejects_invalid_validity_range(db):
    first = make_source(db, "Validity First")
    second = make_source(db, "Validity Second")
    db.add(
        SourceRelation(
            source_id=first.id,
            related_source_id=second.id,
            relation_kind=SourceRelationKind.EDITORIAL_PARENT,
            valid_from=date(2026, 9, 24),
            valid_to=date(2026, 9, 23),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_duplicate_unbounded_source_relation_is_rejected(db):
    first = make_source(db, "Duplicate First")
    second = make_source(db, "Duplicate Second")
    kwargs = {
        "source_id": first.id,
        "related_source_id": second.id,
        "relation_kind": SourceRelationKind.CONTENT_SUPPLIER,
    }
    db.add(SourceRelation(**kwargs))
    db.flush()
    db.add(SourceRelation(**kwargs))
    with pytest.raises(IntegrityError):
        db.flush()


def test_article_provenance_rejects_invalid_confidence(db):
    first = make_source(db, "Confidence First")
    second = make_source(db, "Confidence Second")
    article = make_article(db, first, "article")
    db.add(
        ArticleProvenance(
            article_id=article.id,
            upstream_source_id=second.id,
            relation_kind=ArticleProvenanceKind.SUPPLIED_BY,
            confidence=1.1,
            detection_method=ArticleProvenanceDetectionMethod.MANUAL,
            verified=True,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_article_provenance_rejects_same_upstream_article(db):
    source = make_source(db, "Same Article")
    article = make_article(db, source, "article")
    db.add(
        ArticleProvenance(
            article_id=article.id,
            upstream_source_id=source.id,
            upstream_article_id=article.id,
            relation_kind=ArticleProvenanceKind.REPUBLISHED_FROM,
            confidence=1.0,
            detection_method=ArticleProvenanceDetectionMethod.MANUAL,
            verified=True,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_duplicate_article_provenance_is_rejected(db):
    downstream = make_source(db, "Provenance Downstream")
    upstream = make_source(db, "Provenance Upstream")
    article = make_article(db, downstream, "article")
    kwargs = {
        "article_id": article.id,
        "upstream_source_id": upstream.id,
        "upstream_article_id": None,
        "relation_kind": ArticleProvenanceKind.SUPPLIED_BY,
        "confidence": 0.9,
        "detection_method": ArticleProvenanceDetectionMethod.MANUAL,
        "verified": True,
    }
    db.add(ArticleProvenance(**kwargs))
    db.flush()
    db.add(ArticleProvenance(**kwargs))
    with pytest.raises(IntegrityError):
        db.flush()


def test_soft_deleted_source_relation_can_be_recreated(db):
    first = make_source(db, "Soft Relation First")
    second = make_source(db, "Soft Relation Second")
    first_relation = SourceRelation(
        source_id=first.id,
        related_source_id=second.id,
        relation_kind=SourceRelationKind.CONTENT_SUPPLIER,
    )
    db.add(first_relation)
    db.flush()

    first_relation.deleted_at = datetime.now(UTC)
    db.flush()

    db.add(
        SourceRelation(
            source_id=first.id,
            related_source_id=second.id,
            relation_kind=SourceRelationKind.CONTENT_SUPPLIER,
        )
    )
    db.flush()


def test_soft_deleted_article_provenance_can_be_recreated(db):
    downstream = make_source(db, "Soft Provenance Downstream")
    upstream = make_source(db, "Soft Provenance Upstream")
    article = make_article(db, downstream, "soft-provenance")
    first_provenance = ArticleProvenance(
        article_id=article.id,
        upstream_source_id=upstream.id,
        relation_kind=ArticleProvenanceKind.SUPPLIED_BY,
        confidence=1.0,
        detection_method=ArticleProvenanceDetectionMethod.MANUAL,
        verified=True,
    )
    db.add(first_provenance)
    db.flush()

    first_provenance.deleted_at = datetime.now(UTC)
    db.flush()

    db.add(
        ArticleProvenance(
            article_id=article.id,
            upstream_source_id=upstream.id,
            relation_kind=ArticleProvenanceKind.SUPPLIED_BY,
            confidence=1.0,
            detection_method=ArticleProvenanceDetectionMethod.MANUAL,
            verified=True,
        )
    )
    db.flush()


def test_verified_article_provenance_loads_upstream_chain_recursively(db):
    downstream_source = make_source(db, "Recursive Downstream")
    intermediary_source = make_source(db, "Recursive Intermediary")
    root_source = make_source(db, "Recursive Root")
    downstream_article = make_article(db, downstream_source, "downstream")
    intermediary_article = make_article(db, intermediary_source, "intermediary")

    first = ArticleProvenance(
        article_id=downstream_article.id,
        upstream_source_id=intermediary_source.id,
        upstream_article_id=intermediary_article.id,
        relation_kind=ArticleProvenanceKind.SUPPLIED_BY,
        confidence=1.0,
        detection_method=ArticleProvenanceDetectionMethod.MANUAL,
        verified=True,
    )
    second = ArticleProvenance(
        article_id=intermediary_article.id,
        upstream_source_id=root_source.id,
        relation_kind=ArticleProvenanceKind.REPUBLISHED_FROM,
        confidence=1.0,
        detection_method=ArticleProvenanceDetectionMethod.MANUAL,
        verified=True,
    )
    db.add_all([first, second])
    db.flush()

    rows = SourceDependencyRepository().load_verified_article_provenance(
        db,
        article_ids=[downstream_article.id],
    )

    assert {row.id for row in rows} == {first.id, second.id}
