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


def test_article_provenance_verification_patch_is_explicit_and_idempotent(
    client,
    db,
):
    _, downstream_article = make_article(
        db,
        "Verification Downstream",
        "verification-downstream",
    )
    upstream_source, _ = make_article(
        db,
        "Verification Agency",
        "verification-agency",
    )
    db.commit()

    created = client.post(
        f"/articles/{downstream_article.id}/provenance",
        headers=ADMIN_HEADERS,
        json={
            "upstream_source_id": str(upstream_source.id),
            "relation_kind": "supplied_by",
            "confidence": 0.90,
            "detection_method": "byline",
            "verified": False,
            "notes": "Automatically detected candidate",
        },
    )
    assert created.status_code == 201
    original = created.json()

    url = (
        f"/articles/{downstream_article.id}/provenance/"
        f"{original['id']}"
    )
    verified = client.patch(
        url,
        headers=ADMIN_HEADERS,
        json={"verified": True},
    )
    assert verified.status_code == 200
    body = verified.json()
    assert body["verified"] is True
    assert body["confidence"] == original["confidence"]
    assert body["detection_method"] == original["detection_method"]
    assert body["relation_kind"] == original["relation_kind"]
    assert body["notes"] == original["notes"]

    repeated = client.patch(
        url,
        headers=ADMIN_HEADERS,
        json={"verified": True},
    )
    assert repeated.status_code == 200
    assert repeated.json()["verified"] is True

    revoked = client.patch(
        url,
        headers=ADMIN_HEADERS,
        json={"verified": False},
    )
    assert revoked.status_code == 200
    assert revoked.json()["verified"] is False


def test_article_provenance_verification_patch_requires_admin_key(
    client,
    db,
):
    _, downstream_article = make_article(
        db,
        "Verification Protected Downstream",
        "verification-protected-downstream",
    )
    upstream_source, _ = make_article(
        db,
        "Verification Protected Upstream",
        "verification-protected-upstream",
    )
    db.commit()

    created = client.post(
        f"/articles/{downstream_article.id}/provenance",
        headers=ADMIN_HEADERS,
        json={
            "upstream_source_id": str(upstream_source.id),
            "relation_kind": "supplied_by",
            "verified": False,
        },
    )
    provenance_id = created.json()["id"]

    response = client.patch(
        (
            f"/articles/{downstream_article.id}/provenance/"
            f"{provenance_id}"
        ),
        json={"verified": True},
    )
    assert response.status_code == 401



def test_article_provenance_review_queue_is_admin_only_and_paginated(
    client,
    db,
):
    publisher, first_article = make_article(
        db,
        "Queue Publisher",
        "queue-publisher",
    )
    _, second_article = make_article(
        db,
        "Queue Publisher Two",
        "queue-publisher-two",
    )
    upstream_source, _ = make_article(
        db,
        "Queue Agency",
        "queue-agency",
    )
    db.commit()

    for article, confidence, method in (
        (first_article, 0.90, "byline"),
        (second_article, 0.95, "provider_metadata"),
    ):
        created = client.post(
            f"/articles/{article.id}/provenance",
            headers=ADMIN_HEADERS,
            json={
                "upstream_source_id": str(upstream_source.id),
                "relation_kind": "supplied_by",
                "confidence": confidence,
                "detection_method": method,
                "verified": False,
                "notes": f"Candidate {method}",
            },
        )
        assert created.status_code == 201

    unauthorized = client.get("/article-provenance/review-queue")
    assert unauthorized.status_code == 401

    response = client.get(
        "/article-provenance/review-queue",
        headers=ADMIN_HEADERS,
        params={"limit": 1, "offset": 0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["verified"] is False
    assert item["upstream_source_id"] == str(upstream_source.id)
    assert item["upstream_source_name"] == upstream_source.name
    assert item["publisher_source_id"] in {
        str(publisher.id),
        str(second_article.feed.source_id),
    }
    assert item["provenance_id"]
    assert item["article_id"]


def test_article_provenance_review_queue_filters_candidates(
    client,
    db,
):
    publisher, article = make_article(
        db,
        "Filtered Publisher",
        "filtered-publisher",
    )
    upstream_source, _ = make_article(
        db,
        "Filtered Agency",
        "filtered-agency",
    )
    db.commit()

    created = client.post(
        f"/articles/{article.id}/provenance",
        headers=ADMIN_HEADERS,
        json={
            "upstream_source_id": str(upstream_source.id),
            "relation_kind": "supplied_by",
            "confidence": 0.95,
            "detection_method": "provider_metadata",
            "verified": False,
        },
    )
    assert created.status_code == 201

    response = client.get(
        "/article-provenance/review-queue",
        headers=ADMIN_HEADERS,
        params={
            "upstream_source_id": str(upstream_source.id),
            "publisher_source_id": str(publisher.id),
            "detection_method": "provider_metadata",
            "relation_kind": "supplied_by",
            "min_confidence": 0.94,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["provenance_id"] == created.json()["id"]

    excluded = client.get(
        "/article-provenance/review-queue",
        headers=ADMIN_HEADERS,
        params={"min_confidence": 0.99},
    )
    assert excluded.status_code == 200
    assert excluded.json()["total"] == 0
