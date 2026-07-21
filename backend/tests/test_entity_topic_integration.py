from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.analysis.provider import AnalysisResult, EntityMentionResult, EntityTopicAnalyzer, EntityType, TextPart, TopicResult
from app.enums.article_identity_type import ArticleIdentityType
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.entity import ArticleEntity, Entity, EntityAlias
from app.models.feed import Feed
from app.models.source import Source
from app.models.topic import ArticleTopic, Topic
from app.services.entity_topic_analysis import EntityTopicAnalysisService
from app.services.search_indexing import SearchIndexingService


class FixedAnalyzer(EntityTopicAnalyzer):
    provider = "test"
    version = "1"

    def analyze(self, article):
        return AnalysisResult(
            (EntityMentionResult("OpenAI", "OpenAI", EntityType.ORGANIZATION, .95, .9, TextPart.TITLE, 0, 6, 0), EntityMentionResult("OpenAI", "OpenAI", EntityType.ORGANIZATION, .95, .8, TextPart.BODY, 21, 27, 1)),
            (TopicResult("Artificial Intelligence", .9, .95), TopicResult("Artificial Intelligences", .8, .9)),
        )


class InvalidOffsetAnalyzer(FixedAnalyzer):
    version = "invalid"

    def analyze(self, article):
        return AnalysisResult((EntityMentionResult("OpenAI", "wrong", EntityType.ORGANIZATION, .9, .9, TextPart.BODY, 0, 5, 0),), ())


def create_article(db):
    source = Source(name="Example", normalized_name="example", slug="example", url="https://example.test", source_type=SourceType.NEWS)
    feed = Feed(source=source, name="Main", url="https://example.test/feed")
    article = Article(feed=feed, identity_type=ArticleIdentityType.DERIVED, identity_key="e" * 64, normalized_title="OpenAI news", normalized_text="OpenAI builds tools. OpenAI grows.", language_code="en", content_hash="a" * 64, normalization_version=1, normalized_at=datetime.now(UTC))
    db.add(article)
    db.flush()
    return article


def test_analysis_reuses_entities_topics_and_is_idempotent(db):
    article = create_article(db)
    service = EntityTopicAnalysisService(analyzer=FixedAnalyzer())
    service.analyze_article(db, article)
    assert db.scalar(select(func.count()).select_from(Entity).where(Entity.normalized_name == "openai")) == 1
    assert db.scalar(select(func.count()).select_from(ArticleEntity)) == 2
    assert db.scalar(select(func.count()).select_from(Topic).where(Topic.normalized_name == "artificial intelligence")) == 1
    assert db.scalar(select(func.count()).select_from(ArticleTopic)) == 1
    service.analyze_article(db, article)
    assert db.scalar(select(func.count()).select_from(ArticleEntity)) == 2


def test_alias_resolution_and_entity_type_separation(db):
    article = create_article(db)
    organization = Entity(canonical_name="OpenAI", normalized_name="openai", entity_type=EntityType.ORGANIZATION)
    person = Entity(canonical_name="Open Ai", normalized_name="open ai", entity_type=EntityType.PERSON)
    db.add_all([organization, person])
    db.flush()
    db.add(EntityAlias(entity_id=organization.id, original_alias="Open AI", normalized_alias="open ai", entity_type=EntityType.ORGANIZATION))
    service = EntityTopicAnalysisService(analyzer=FixedAnalyzer())
    service.analyze_article(db, article)
    assert db.scalar(select(func.count()).select_from(Entity).where(Entity.normalized_name.in_(["openai", "open ai"]))) == 2


def test_alias_resolution_normalizes_stored_aliases(db):
    article = create_article(db)
    existing = Entity(canonical_name="Open Artificial Intelligence", normalized_name="open artificial intelligence", entity_type=EntityType.ORGANIZATION)
    db.add(existing)
    db.flush()
    db.add(EntityAlias(entity_id=existing.id, original_alias="  OPENAI! ", normalized_alias="openai", entity_type=EntityType.ORGANIZATION))
    db.flush()
    EntityTopicAnalysisService(analyzer=FixedAnalyzer()).analyze_article(db, article)
    assert db.scalar(select(func.count()).select_from(Entity).where(Entity.normalized_name.in_(["openai", "open artificial intelligence"]))) == 1
    assert db.scalar(select(ArticleEntity.entity_id)) == existing.id


def test_api_and_search_filters(db, client):
    article = create_article(db)
    EntityTopicAnalysisService(analyzer=FixedAnalyzer()).analyze_article(db, article)
    SearchIndexingService().index_article(db, article)
    db.flush()
    entity = db.scalar(select(Entity).where(Entity.normalized_name == "openai"))
    topic = db.scalar(select(Topic).where(Topic.normalized_name == "artificial intelligence"))
    mentions = client.get(f"/articles/{article.id}/entities").json()[0]["mentions"]
    assert {(mention["text_source"], mention["start_offset"]) for mention in mentions} == {("title", 0), ("body", 21)}
    assert client.get(f"/entities/{entity.id}").json()["article_count"] == 1
    assert client.get(f"/topics/{topic.id}").json()["article_count"] == 1
    assert client.get("/entities", params={"entity_type": "organization", "query": "openai"}).json()["total"] == 1
    assert client.get("/search", params={"entity_id": str(entity.id)}).json()["total"] == 1
    assert client.get("/search", params={"topic_slug": topic.slug}).json()["total"] == 1
    assert client.get("/search", params={"entity_type": "not-a-type"}).status_code == 422
    assert client.get("/entities", params={"query": "x" * 501}).status_code == 422
    assert client.get("/topics", params={"query": "x" * 501}).status_code == 422


def test_invalid_provider_result_preserves_previous_analysis(db):
    article = create_article(db)
    EntityTopicAnalysisService(analyzer=FixedAnalyzer()).analyze_article(db, article)
    previous_ids = set(db.scalars(select(ArticleEntity.id).where(ArticleEntity.article_id == article.id)).all())
    with pytest.raises(ValueError, match="do not match"):
        EntityTopicAnalysisService(analyzer=InvalidOffsetAnalyzer()).analyze_article(db, article)
    assert set(db.scalars(select(ArticleEntity.id).where(ArticleEntity.article_id == article.id)).all()) == previous_ids


def test_article_endpoints_exclude_soft_deleted_entities_and_topics(db, client):
    article = create_article(db)
    EntityTopicAnalysisService(analyzer=FixedAnalyzer()).analyze_article(db, article)
    entity = db.scalar(select(Entity).where(Entity.normalized_name == "openai"))
    topic = db.scalar(select(Topic).where(Topic.normalized_name == "artificial intelligence"))
    entity.deleted_at = topic.deleted_at = datetime.now(UTC)
    db.flush()
    assert client.get(f"/articles/{article.id}/entities").json() == []
    assert client.get(f"/articles/{article.id}/topics").json() == []
