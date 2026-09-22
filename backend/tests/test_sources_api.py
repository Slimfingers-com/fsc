import pytest

from app.core.settings import settings
from app.enums.source_metadata import PublicationForm, SourceMedium
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



def test_create_source_with_catalog_outlet(client):
    response = client.post(
        "/sources",
        headers=ADMIN_HEADERS,
        json={
            "name": "Print Example",
            "url": "https://print.example.com",
            "source_type": "NEWS",
            "country": "DE",
            "language": "de",
            "outlets": [
                {
                    "name": "Weekly Print",
                    "media_category": "print",
                    "publication_form": "weekly_newspaper",
                    "publication_frequency": "weekly",
                    "language": "de",
                    "is_primary": True,
                }
            ],
        },
    )

    assert response.status_code == 201

    detail_response = client.get("/sources/print-example")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["outlets"]) == 1
    outlet = detail["outlets"][0]
    assert outlet["media_category"] == SourceMedium.PRINT
    assert outlet["publication_form"] == PublicationForm.WEEKLY_NEWSPAPER
    assert outlet["publication_frequency"] == "weekly"
    assert outlet["is_primary"] is True


def test_source_classification_outlet_and_metric_round_trip(client):
    source_response = client.post(
        "/sources",
        headers=ADMIN_HEADERS,
        json={
            "name": "Catalog Example",
            "url": "https://catalog.example.com",
            "source_type": "NEWS",
            "country": "DE",
            "language": "de",
        },
    )
    assert source_response.status_code == 201

    outlet_response = client.post(
        "/sources/catalog-example/outlets",
        headers=ADMIN_HEADERS,
        json={
            "name": "Print Magazine",
            "media_category": "print",
            "publication_form": "magazine",
            "publication_frequency": "monthly",
            "language": "de",
            "is_primary": True,
        },
    )
    assert outlet_response.status_code == 201
    outlet = outlet_response.json()
    outlet_id = outlet["id"]

    classification_response = client.post(
        "/sources/catalog-example/classifications",
        headers=ADMIN_HEADERS,
        json={
            "dimension": "editorial_orientation",
            "value": "example-position",
            "classifier_type": "media_database",
            "classifier_name": "Example Media Database",
            "source_url": "https://classification.example.com/item",
            "reference_date": "2026-09-22",
            "valid_from": "2026-01-01",
        },
    )
    assert classification_response.status_code == 201
    classification = classification_response.json()
    assert classification["value"] == "example-position"
    assert classification["classifier_type"] == "media_database"

    metric_response = client.post(
        "/sources/catalog-example/metrics",
        headers=ADMIN_HEADERS,
        json={
            "outlet_id": outlet_id,
            "metric_kind": "sold_circulation",
            "value": 12345,
            "unit": "count",
            "metric_scope": "print_total",
            "reference_period": "Q2/2026",
            "period_start": "2026-04-01",
            "period_end": "2026-06-30",
            "measurement_body": "Example Audit Body",
            "source_url": "https://metrics.example.com/q2-2026",
            "audited": True,
        },
    )
    assert metric_response.status_code == 201
    metric = metric_response.json()
    assert metric["outlet_id"] == outlet_id
    assert metric["metric_kind"] == "sold_circulation"
    assert metric["value"] == 12345
    assert metric["audited"] is True

    detail_response = client.get("/sources/catalog-example")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["outlets"]) == 1
    assert detail["outlets"][0]["name"] == "Print Magazine"
    assert len(detail["classifications"]) == 1
    assert detail["classifications"][0]["value"] == "example-position"
    assert len(detail["metrics"]) == 1
    assert detail["metrics"][0]["value"] == 12345


def test_source_metadata_admin_endpoints_require_admin_key(client, db):
    service = SourceService()
    service.create_source(
        db,
        SourceCreate(
            name="Protected Metadata",
            url="https://protected.example.com",
            source_type=SourceType.NEWS,
        ),
    )
    db.commit()

    outlet_response = client.post(
        "/sources/protected-metadata/outlets",
        json={
            "name": "Print",
            "media_category": "print",
            "publication_form": "magazine",
        },
    )
    classification_response = client.post(
        "/sources/protected-metadata/classifications",
        json={
            "dimension": "editorial_orientation",
            "value": "example",
            "classifier_type": "self_description",
            "classifier_name": "Protected Metadata",
            "source_url": "https://protected.example.com/about",
            "reference_date": "2026-09-22",
        },
    )
    metric_response = client.post(
        "/sources/protected-metadata/metrics",
        json={
            "metric_kind": "subscribers",
            "value": 100,
            "reference_period": "2026",
            "measurement_body": "Publisher",
            "source_url": "https://protected.example.com/media",
        },
    )

    assert outlet_response.status_code == 401
    assert classification_response.status_code == 401
    assert metric_response.status_code == 401


def test_source_metric_rejects_outlet_from_other_source(client):
    for name in ("First Source", "Second Source"):
        response = client.post(
            "/sources",
            headers=ADMIN_HEADERS,
            json={
                "name": name,
                "url": f"https://{name.lower().replace(' ', '-')}.example.com",
                "source_type": "NEWS",
            },
        )
        assert response.status_code == 201

    outlet_response = client.post(
        "/sources/first-source/outlets",
        headers=ADMIN_HEADERS,
        json={
            "name": "Print",
            "media_category": "print",
            "publication_form": "magazine",
        },
    )
    assert outlet_response.status_code == 201
    outlet_id = outlet_response.json()["id"]

    response = client.post(
        "/sources/second-source/metrics",
        headers=ADMIN_HEADERS,
        json={
            "outlet_id": outlet_id,
            "metric_kind": "subscribers",
            "value": 100,
            "reference_period": "2026",
            "measurement_body": "Publisher",
            "source_url": "https://metrics.example.com/2026",
        },
    )

    assert response.status_code == 422


def test_source_metric_rejects_invalid_period(client, db):
    service = SourceService()
    service.create_source(
        db,
        SourceCreate(
            name="Invalid Metric",
            url="https://invalid-metric.example.com",
            source_type=SourceType.NEWS,
        ),
    )
    db.commit()

    response = client.post(
        "/sources/invalid-metric/metrics",
        headers=ADMIN_HEADERS,
        json={
            "metric_kind": "print_run",
            "value": 100,
            "reference_period": "Q2/2026",
            "period_start": "2026-06-30",
            "period_end": "2026-04-01",
            "measurement_body": "Publisher",
            "source_url": "https://invalid-metric.example.com/media",
        },
    )

    assert response.status_code == 422
