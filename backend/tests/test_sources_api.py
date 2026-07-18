from app.enums.source_type import SourceType
from app.schemas.feed import FeedCreate
from app.schemas.source import SourceCreate
from app.services.source import SourceService


def test_get_source_by_slug(client, db):
    service = SourceService()

    created = service.create_source(
        db=db,
        data=SourceCreate(
            name="BBC News",
            url="https://www.bbc.com",
            source_type=SourceType.NEWS,
            feeds=[
                FeedCreate(
                    name="Top Stories",
                    url="https://feeds.bbci.co.uk/news/rss.xml",
                    priority=1,
                    fetch_interval_minutes=15,
                ),
            ],
        ),
    )

    response = client.get(f"/sources/{created.slug}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(created.id)
    assert data["name"] == "BBC News"
    assert data["slug"] == created.slug
    assert "rss_url" not in data

    assert len(data["feeds"]) == 1
    assert data["feeds"][0]["name"] == "Top Stories"
    assert data["feeds"][0]["url"] == (
        "https://feeds.bbci.co.uk/news/rss.xml"
    )
    assert data["feeds"][0]["priority"] == 1
    assert data["feeds"][0]["fetch_interval_minutes"] == 15
    assert data["feeds"][0]["active"] is True


def test_get_unknown_source_returns_404(client):
    response = client.get("/sources/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Source not found.",
    }


def test_list_sources(client, db):
    service = SourceService()

    service.create_source(
        db=db,
        data=SourceCreate(
            name="BBC News",
            url="https://www.bbc.com",
            source_type=SourceType.NEWS,
            feeds=[
                FeedCreate(
                    name="Top Stories",
                    url="https://feeds.bbci.co.uk/news/rss.xml",
                ),
            ],
        ),
    )

    service.create_source(
        db=db,
        data=SourceCreate(
            name="CNN",
            url="https://www.cnn.com",
            source_type=SourceType.NEWS,
            feeds=[
                FeedCreate(
                    name="Main Feed",
                    url="https://www.cnn.com/rss/edition.rss",
                ),
            ],
        ),
    )

    response = client.get("/sources")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["name"] == "BBC News"
    assert data[0]["feeds"][0]["name"] == "Top Stories"
    assert data[1]["name"] == "CNN"
    assert data[1]["feeds"][0]["name"] == "Main Feed"


def test_create_source(client):
    response = client.post(
        "/sources",
        json={
            "name": "Reuters",
            "url": "https://www.reuters.com",
            "source_type": "AGENCY",
            "feeds": [
                {
                    "name": "World News",
                    "url": "https://www.reutersagency.com/feed/",
                    "priority": 1,
                    "fetch_interval_minutes": 10,
                },
                {
                    "name": "Business News",
                    "url": "https://www.reutersagency.com/business-feed/",
                    "priority": 2,
                    "fetch_interval_minutes": 20,
                },
            ],
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Reuters"
    assert data["slug"] == "reuters"
    assert data["url"] == "https://www.reuters.com/"
    assert data["source_type"] == "AGENCY"
    assert "rss_url" not in data

    assert len(data["feeds"]) == 2

    assert data["feeds"][0]["name"] == "World News"
    assert data["feeds"][0]["url"] == (
        "https://www.reutersagency.com/feed/"
    )
    assert data["feeds"][0]["priority"] == 1
    assert data["feeds"][0]["fetch_interval_minutes"] == 10

    assert data["feeds"][1]["name"] == "Business News"
    assert data["feeds"][1]["url"] == (
        "https://www.reutersagency.com/business-feed/"
    )
    assert data["feeds"][1]["priority"] == 2
    assert data["feeds"][1]["fetch_interval_minutes"] == 20


def test_create_source_without_feeds(client):
    response = client.post(
        "/sources",
        json={
            "name": "Example News",
            "url": "https://example.com",
            "source_type": "NEWS",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Example News"
    assert data["feeds"] == []


def test_create_duplicate_source_returns_409(client):
    payload = {
        "name": "Reuters",
        "url": "https://www.reuters.com",
        "source_type": "AGENCY",
        "feeds": [],
    }

    first_response = client.post(
        "/sources",
        json=payload,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/sources",
        json=payload,
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": 'Die Quelle "Reuters" existiert bereits.',
    }
