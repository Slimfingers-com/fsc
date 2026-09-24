from uuid import uuid4

import pytest

from app.core.settings import settings
from app.enums.article_identity_type import ArticleIdentityType
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.feed import Feed
from app.schemas.source import SourceCreate
from app.services.source import SourceService


ADMIN_KEY = "test-source-admin-key"
ADMIN_HEADERS = {
    "X-FSC-Admin-Key": ADMIN_KEY,
}


@pytest.fixture(autouse=True)
def configure_source_admin_key(monkeypatch):
    monkeypatch.setattr(
        settings,
        "source_admin_api_key",
        ADMIN_KEY,
    )


def make_article(db, source_name: str, suffix: str):
    source = SourceService().create_source(
        db,
        SourceCreate(
            name=source_name,
            url=f"https://{suffix}.example.com",
            source_type=SourceType.NEWS,
        ),
    )
    feed = Feed(
        source=source,
        name="Main",
        url=f"https://{suffix}.example.com/feed.xml",
    )
    article = Article(
        feed=feed,
        identity_type=ArticleIdentityType.DERIVED,
        identity_key=uuid4().hex * 2,
        title=f"Article {suffix}",
    )
    db.add(article)
    db.flush()
    return source, article


def test_article_provenance_round_trip(client, db):
    downstream_source, downstream_article = make_article(
        db,
        "Downstream News",
        "downstream",
    )
    upstream_source, upstream_article = make_article(
        db,
        "Upstream Agency",
        "upstream",
    )
    db.commit()

    response = client.post(
        f"/articles/{downstream_article.id}/provenance",
        headers=ADMIN_HEADERS,
        json={
            "upstream_source_id": str(upstream_source.id),
            "upstream_article_id": str(upstream_article.id),
            "relation_kind": "supplied_by",
            "confidence": 0.98,
            "detection_method": "provider_metadata",
            "verified": True,
            "provenance_url": "https://upstream.example.com/provenance",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["article_id"] == str(downstream_article.id)
    assert body["upstream_source_id"] == str(upstream_source.id)
    assert body["upstream_article_id"] == str(upstream_article.id)
    assert body["verified"] is True

    listing = client.get(
        f"/articles/{downstream_article.id}/provenance"
    )
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [body["id"]]
    assert downstream_source.id != upstream_source.id


def test_article_provenance_rejects_upstream_article_from_other_source(
    client,
    db,
):
    _, downstream_article = make_article(
        db,
        "Mismatch Downstream",
        "mismatch-downstream",
    )
    declared_upstream, _ = make_article(
        db,
        "Declared Upstream",
        "declared-upstream",
    )
    _, wrong_article = make_article(
        db,
        "Wrong Article Source",
        "wrong-article",
    )
    db.commit()

    response = client.post(
        f"/articles/{downstream_article.id}/provenance",
        headers=ADMIN_HEADERS,
        json={
            "upstream_source_id": str(declared_upstream.id),
            "upstream_article_id": str(wrong_article.id),
            "relation_kind": "republished_from",
            "verified": True,
        },
    )
    assert response.status_code == 422
    assert "gehört nicht" in response.json()["detail"]


def test_article_provenance_requires_admin_key(client, db):
    _, downstream_article = make_article(
        db,
        "Protected Downstream",
        "protected-downstream",
    )
    upstream_source, _ = make_article(
        db,
        "Protected Upstream",
        "protected-upstream",
    )
    db.commit()

    response = client.post(
        f"/articles/{downstream_article.id}/provenance",
        json={
            "upstream_source_id": str(upstream_source.id),
            "relation_kind": "supplied_by",
        },
    )
    assert response.status_code == 401
