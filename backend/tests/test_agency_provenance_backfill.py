from uuid import uuid4

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.source_dependency import (
    ArticleProvenanceDetectionMethod,
    ArticleProvenanceKind,
    ArticleProvenanceReviewStatus,
)
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.feed import Feed
from app.repositories.source_dependency import SourceDependencyRepository
from app.schemas.source import SourceCreate
from app.services.agency_provenance_backfill import (
    AgencyProvenanceBackfiller,
)
from app.services.source import SourceService


def _source(db, name: str, suffix: str, source_type=SourceType.NEWS):
    return SourceService().create_source(
        db,
        SourceCreate(
            name=name,
            url=f"https://{suffix}.example.com",
            source_type=source_type,
        ),
    )


def _article(db, source, suffix: str, author: str):
    feed = next(
        (item for item in source.feeds if item.deleted_at is None),
        None,
    )
    if feed is None:
        feed = Feed(
            source=source,
            name="Main",
            url=f"https://{suffix}.example.com/feed.xml",
        )
        db.add(feed)
    article = Article(
        feed=feed,
        identity_type=ArticleIdentityType.DERIVED,
        identity_key=uuid4().hex * 2,
        title=f"Article {suffix}",
        author=author,
    )
    db.add(article)
    db.flush()
    return article


def test_agency_provenance_backfill_is_unverified_and_idempotent(db):
    agency = _source(
        db,
        "Associated Press",
        "ap",
        SourceType.AGENCY,
    )
    downstream = _source(db, "Historical News", "historical")
    first = _article(
        db,
        downstream,
        "historical-1",
        "Associated Press",
    )
    second = _article(
        db,
        downstream,
        "historical-2",
        "Jane Doe, Associated Press",
    )
    _article(
        db,
        downstream,
        "historical-3",
        "The Associated Press",
    )

    backfiller = AgencyProvenanceBackfiller()
    report = backfiller.backfill(db)

    assert report.scanned_articles == 3
    assert report.detected_candidates == 2
    assert report.change_count == 2
    assert report.already_present == 0
    assert report.changes_by_source == {"associated-press": 2}

    repository = SourceDependencyRepository()
    rows = (
        repository.list_article_provenance(db, article_id=first.id)
        + repository.list_article_provenance(db, article_id=second.id)
    )
    assert len(rows) == 2
    assert all(row.upstream_source_id == agency.id for row in rows)
    assert all(
        row.relation_kind == ArticleProvenanceKind.SUPPLIED_BY
        for row in rows
    )
    assert all(
        row.detection_method == ArticleProvenanceDetectionMethod.BYLINE
        for row in rows
    )
    assert all(row.confidence == 0.90 for row in rows)
    assert all(row.review_status is ArticleProvenanceReviewStatus.PENDING for row in rows)

    repeated = backfiller.backfill(db)
    assert repeated.detected_candidates == 2
    assert repeated.change_count == 0
    assert repeated.already_present == 2
    assert (
        len(repository.list_article_provenance(db, article_id=first.id))
        == 1
    )


def test_agency_provenance_backfill_fails_closed_for_missing_and_self(db):
    associated_press = _source(
        db,
        "Associated Press",
        "ap-self",
        SourceType.AGENCY,
    )
    _article(
        db,
        associated_press,
        "ap-self",
        "Associated Press",
    )

    downstream = _source(db, "Missing Upstream News", "missing-upstream")
    missing = _article(
        db,
        downstream,
        "missing-upstream",
        "Reuters",
    )

    report = AgencyProvenanceBackfiller().backfill(db)

    assert report.detected_candidates == 2
    assert report.change_count == 0
    assert report.missing_upstream_source == 1
    assert report.self_dependencies_skipped == 1
    assert (
        SourceDependencyRepository().list_article_provenance(
            db,
            article_id=missing.id,
        )
        == []
    )
