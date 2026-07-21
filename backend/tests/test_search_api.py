from datetime import UTC, datetime, timedelta

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from app.services.search_indexing import SearchIndexingService


def add_indexed_article(db, *, source_name, source_slug, title, body, language, published_at):
    source = Source(
        name=source_name, normalized_name=source_slug, slug=source_slug,
        url=f"https://{source_slug}.test", source_type=SourceType.NEWS,
    )
    feed = Feed(source=source, name="Main", url=f"https://{source_slug}.test/feed")
    article = Article(
        feed=feed, identity_type=ArticleIdentityType.DERIVED,
        identity_key=(source_slug + title).ljust(64, "0")[:64],
        normalized_title=title, normalized_text=body, language_code=language,
        content_hash=(source_slug[0] * 64), normalization_version=1,
        normalized_at=datetime.now(UTC), published_at=published_at,
        link=f"https://{source_slug}.test/article",
    )
    db.add(article)
    db.flush()
    SearchIndexingService().index_article(db, article)
    db.flush()
    return article


def test_search_api_full_text_filters_sort_and_pagination(client, db):
    now = datetime.now(UTC)
    add_indexed_article(db, source_name="Alpha", source_slug="alpha", title="Climate policy", body="European climate reform", language="en", published_at=now)
    add_indexed_article(db, source_name="Beta", source_slug="beta", title="Climate report", body="A climate science report", language="en", published_at=now - timedelta(days=1))
    add_indexed_article(db, source_name="Gamma", source_slug="gamma", title="Wirtschaft", body="Deutsche Wirtschaft", language="de", published_at=now)

    response = client.get("/search", params={"q": "climate", "language": "en", "sort": "newest", "page_size": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["pages"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["source_slug"] == "alpha"
    assert "<mark>" in data["items"][0]["excerpt"]

    filtered = client.get("/search", params={"source": "beta"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["title"] == "Climate report"


def test_search_api_rejects_invalid_pagination(client):
    response = client.get("/search", params={"page": 0})
    assert response.status_code == 422


def test_search_excludes_deleted_and_inactive_entities(client, db):
    now = datetime.now(UTC)
    entities = []
    for slug in ("active", "article-deleted", "feed-inactive", "source-deleted"):
        article = add_indexed_article(
            db, source_name=slug, source_slug=slug, title="Visible topic",
            body="Searchable body", language="en", published_at=now,
        )
        entities.append(article)
    entities[1].deleted_at = now
    entities[2].feed.active = False
    entities[3].feed.source.deleted_at = now
    db.flush()
    response = client.get("/search", params={"q": "searchable"})
    assert response.status_code == 200
    assert [item["source_slug"] for item in response.json()["items"]] == ["active"]
