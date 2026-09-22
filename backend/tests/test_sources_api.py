import pytest

from app.core.settings import settings
from app.enums.source_type import SourceType
from app.schemas.feed import FeedCreate
from app.schemas.source import SourceCreate
from app.services.source import SourceService


ADMIN_KEY = "test-source-admin-key"
ADMIN_HEADERS = {
    "X-FSC-Admin-Key": ADMIN_KEY,
}


@pytest.fixture(autouse=True)
def configure_source_admin_key(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "source_admin_api_key",
        ADMIN_KEY,
    )


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
        headers=ADMIN_HEADERS,
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
        headers=ADMIN_HEADERS,
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
        headers=ADMIN_HEADERS,
        json=payload,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/sources",
        headers=ADMIN_HEADERS,
        json=payload,
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": 'Die Quelle "Reuters" existiert bereits.',
    }

def test_create_source_requires_admin_key(
    client,
):
    response = client.post(
        "/sources",
        json={
            "name": "Unauthorized",
            "url": "https://unauthorized.example.com",
            "source_type": "NEWS",
        },
    )

    assert response.status_code == 401


def test_create_source_fails_closed_when_admin_key_is_not_configured(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "source_admin_api_key",
        "",
    )

    response = client.post(
        "/sources",
        headers=ADMIN_HEADERS,
        json={
            "name": "No Admin Config",
            "url": "https://no-admin.example.com",
            "source_type": "NEWS",
        },
    )

    assert response.status_code == 503


def test_source_business_rule_violation_returns_422(
    client,
):
    response = client.post(
        "/sources",
        headers=ADMIN_HEADERS,
        json={
            "name": "Duplicate Feed Names",
            "url": "https://duplicate-feed.example.com",
            "source_type": "NEWS",
            "feeds": [
                {
                    "name": "Main",
                    "url": (
                        "https://duplicate-feed.example.com/"
                        "one.xml"
                    ),
                },
                {
                    "name": "main",
                    "url": (
                        "https://duplicate-feed.example.com/"
                        "two.xml"
                    ),
                },
            ],
        },
    )

    assert response.status_code == 422


def test_update_source_metadata(client):
    created = client.post(
        "/sources",
        headers=ADMIN_HEADERS,
        json={
            "name": "Example Weekly",
            "url": "https://weekly.example.com",
            "source_type": "NEWS",
        },
    )
    assert created.status_code == 201
    slug = created.json()["slug"]

    response = client.patch(
        f"/sources/{slug}",
        headers=ADMIN_HEADERS,
        json={
            "country": "de",
            "language": "de",
            "content_languages": ["DE", "en", "de"],
            "media_family": "PRINT",
            "publication_format": "WEEKLY_NEWSPAPER",
            "publication_frequency": "WEEKLY",
            "coverage_countries": ["de", "AT", "de"],
            "ownership": "Example Publisher",
            "paywall": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["country"] == "DE"
    assert data["language"] == "de"
    assert data["content_languages"] == ["de", "en"]
    assert data["media_family"] == "PRINT"
    assert data["publication_format"] == "WEEKLY_NEWSPAPER"
    assert data["publication_frequency"] == "WEEKLY"
    assert data["coverage_countries"] == ["DE", "AT"]
    assert data["ownership"] == "Example Publisher"
    assert data["paywall"] is True


def test_source_classification_keeps_history(client):
    created = client.post(
        "/sources",
        headers=ADMIN_HEADERS,
        json={
            "name": "Classification Example",
            "url": "https://classification.example.com",
            "source_type": "NEWS",
        },
    )
    slug = created.json()["slug"]

    first = client.post(
        f"/sources/{slug}/classifications",
        headers=ADMIN_HEADERS,
        json={
            "kind": "POLITICAL_ORIENTATION",
            "value": "CENTER_RIGHT",
            "detail": "first sourced classification",
            "evidence_source_name": "Research A",
            "as_of": "2025-01-01",
        },
    )
    assert first.status_code == 201

    second = client.post(
        f"/sources/{slug}/classifications",
        headers=ADMIN_HEADERS,
        json={
            "kind": "POLITICAL_ORIENTATION",
            "value": "CONSERVATIVE",
            "detail": "newer sourced classification",
            "evidence_source_name": "Research B",
            "as_of": "2026-09-01",
        },
    )
    assert second.status_code == 201

    classifications = second.json()["classifications"]
    assert len(classifications) == 2
    by_value = {item["value"]: item for item in classifications}
    assert by_value["CENTER_RIGHT"]["is_primary"] is False
    assert by_value["CONSERVATIVE"]["is_primary"] is True


def test_add_source_reach_metric_with_quality(client):
    created = client.post(
        "/sources",
        headers=ADMIN_HEADERS,
        json={
            "name": "Reach Example",
            "url": "https://reach.example.com",
            "source_type": "NEWS",
        },
    )
    slug = created.json()["slug"]

    response = client.post(
        f"/sources/{slug}/reach-metrics",
        headers=ADMIN_HEADERS,
        json={
            "metric_type": "PRINT_SOLD_CIRCULATION",
            "metric_value": 42000,
            "period_start": "2026-04-01",
            "period_end": "2026-06-30",
            "evidence_source_name": "Publisher Media Data",
            "quality": "PUBLISHER_REPORTED",
        },
    )

    assert response.status_code == 201
    metrics = response.json()["reach_metrics"]
    assert len(metrics) == 1
    assert metrics[0]["metric_value"] == 42000
    assert metrics[0]["quality"] == "PUBLISHER_REPORTED"


def test_update_source_requires_admin_key(client):
    created = client.post(
        "/sources",
        headers=ADMIN_HEADERS,
        json={
            "name": "Protected Update",
            "url": "https://protected-update.example.com",
            "source_type": "NEWS",
        },
    )
    slug = created.json()["slug"]

    response = client.patch(
        f"/sources/{slug}",
        json={"ownership": "Unauthorized Change"},
    )

    assert response.status_code == 401

