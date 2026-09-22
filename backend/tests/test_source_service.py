from datetime import UTC, datetime

import pytest

from app.core.exceptions import DuplicateSourceError
from app.enums.source_metadata import PublicationForm, SourceMedium
from app.enums.source_type import SourceType
from app.schemas.feed import FeedCreate
from app.schemas.source_metadata import SourceOutletCreate
from app.schemas.source import SourceCreate
from app.services.source import SourceService


def test_create_source(db):
    service = SourceService()

    source = service.create_source(
        db,
        SourceCreate(
            name="Reuters",
            url="https://www.reuters.com",
            source_type=SourceType.AGENCY,
            outlets=[
                SourceOutletCreate(
                    name="Reuters Agency",
                    media_category=SourceMedium.AGENCY,
                    publication_form=PublicationForm.NEWS_AGENCY,
                    publication_frequency="continuous",
                    is_primary=True,
                ),
            ],
            feeds=[
                FeedCreate(
                    name="World News",
                    url="https://www.reutersagency.com/feed/",
                    priority=1,
                    fetch_interval_minutes=15,
                ),
            ],
        ),
    )

    assert source.name == "Reuters"
    assert source.normalized_name == "reuters"
    assert source.slug == "reuters"
    assert len(source.outlets) == 1
    assert source.outlets[0].media_category == SourceMedium.AGENCY
    assert source.outlets[0].publication_form == PublicationForm.NEWS_AGENCY
    assert source.outlets[0].publication_frequency == "continuous"

    assert len(source.feeds) == 1
    assert source.feeds[0].name == "World News"
    assert source.feeds[0].url == "https://www.reutersagency.com/feed/"
    assert source.feeds[0].priority == 1
    assert source.feeds[0].fetch_interval_minutes == 15
    assert source.feeds[0].active is True


def test_duplicate_source_name_is_rejected(db):
    service = SourceService()

    service.create_source(
        db,
        SourceCreate(
            name="Reuters",
            url="https://www.reuters.com",
            source_type=SourceType.AGENCY,
        ),
    )

    with pytest.raises(DuplicateSourceError):
        service.create_source(
            db,
            SourceCreate(
                name="reuters",
                url="https://www.reuters.com",
                source_type=SourceType.AGENCY,
            ),
        )


def test_get_source_by_slug(db):
    service = SourceService()

    created_source = service.create_source(
        db,
        SourceCreate(
            name="Reuters",
            url="https://www.reuters.com",
            source_type=SourceType.AGENCY,
            feeds=[
                FeedCreate(
                    name="World News",
                    url="https://www.reutersagency.com/feed/",
                ),
            ],
        ),
    )

    found_source = service.get_by_slug(db, "reuters")

    assert found_source is not None
    assert found_source.id == created_source.id
    assert len(found_source.feeds) == 1
    assert found_source.feeds[0].name == "World News"


def test_get_source_by_unknown_slug_returns_none(db):
    service = SourceService()

    source = service.get_by_slug(db, "does-not-exist")

    assert source is None


def test_list_active_sources(db):
    service = SourceService()

    active_source = service.create_source(
        db,
        SourceCreate(
            name="Reuters",
            url="https://www.reuters.com",
            source_type=SourceType.AGENCY,
            feeds=[
                FeedCreate(
                    name="World News",
                    url="https://www.reutersagency.com/feed/",
                ),
            ],
        ),
    )

    inactive_source = service.create_source(
        db,
        SourceCreate(
            name="Associated Press",
            url="https://apnews.com",
            source_type=SourceType.AGENCY,
        ),
    )
    inactive_source.active = False
    db.flush()

    sources = service.list_active(db)

    assert sources == [active_source]
    assert len(sources[0].feeds) == 1

def test_source_reads_exclude_soft_deleted_feeds(
    db,
):
    service = SourceService()

    source = service.create_source(
        db,
        SourceCreate(
            name="Soft Delete News",
            url="https://soft-delete.example.com",
            source_type=SourceType.NEWS,
            feeds=[
                FeedCreate(
                    name="Visible",
                    url=(
                        "https://soft-delete.example.com/"
                        "visible.xml"
                    ),
                ),
                FeedCreate(
                    name="Deleted",
                    url=(
                        "https://soft-delete.example.com/"
                        "deleted.xml"
                    ),
                ),
            ],
        ),
    )

    source.feeds[1].deleted_at = (
        datetime.now(UTC)
    )
    db.flush()

    by_slug = service.get_by_slug(
        db,
        source.slug,
    )
    listed = service.list_active(
        db
    )

    assert by_slug is not None
    assert [
        feed.name
        for feed in by_slug.feeds
    ] == [
        "Visible",
    ]
    assert [
        feed.name
        for feed in listed[0].feeds
    ] == [
        "Visible",
    ]
