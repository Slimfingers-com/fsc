from datetime import UTC, datetime

from sqlalchemy import func, select

from app.analysis.provider import AnalysisResult, EntityMentionResult, EntityTopicAnalyzer, EntityType, TopicResult
from app.enums.article_identity_type import ArticleIdentityType
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.entity import ArticleEntity, Entity
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
            (EntityMentionResult("OpenAI", "OpenAI", EntityType.ORGANIZATION, .95, .9, 0, 6, 0), EntityMentionResult("OpenAI", "OpenAI", EntityType.ORGANIZATION, .95, .8, 20, 26, 1)),
            (TopicResult("Artificial Intelligence", .9, .95), TopicResult("Artificial Intelligences", .8, .9)),
        )


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
    assert db.scalar(select(func.count()).select_from(Entity)) == 1
    assert db.scalar(select(func.count()).select_from(ArticleEntity)) == 2
    assert db.scalar(select(func.count()).select_from(Topic)) == 1
    assert db.scalar(select(func.count()).select_from(ArticleTopic)) == 1
    service.analyze_article(db, article)
    assert db.scalar(select(func.count()).select_from(ArticleEntity)) == 2


def test_alias_resolution_and_entity_type_separation(db):
    article = create_article(db)
    db.add(Entity(canonical_name="OpenAI", normalized_name="openai", entity_type=EntityType.ORGANIZATION, aliases=["open ai"]))
    db.add(Entity(canonical_name="Open Ai", normalized_name="open ai", entity_type=EntityType.PERSON, aliases=[]))
    db.flush()
    service = EntityTopicAnalysisService(analyzer=FixedAnalyzer())
    service.analyze_article(db, article)
    assert db.scalar(select(func.count()).select_from(Entity)) == 2


def test_alias_resolution_normalizes_stored_aliases(db):
    article = create_article(db)
    existing = Entity(canonical_name="Open Artificial Intelligence", normalized_name="open artificial intelligence", entity_type=EntityType.ORGANIZATION, aliases=["  OPENAI! "])
    db.add(existing)
    db.flush()
    EntityTopicAnalysisService(analyzer=FixedAnalyzer()).analyze_article(db, article)
    assert db.scalar(select(func.count()).select_from(Entity)) == 1
    assert db.scalar(select(ArticleEntity.entity_id)) == existing.id


def test_api_and_search_filters(db, client):
    article = create_article(db)
    EntityTopicAnalysisService(analyzer=FixedAnalyzer()).analyze_article(db, article)
    SearchIndexingService().index_article(db, article)
    db.flush()
    entity = db.scalar(select(Entity))
    topic = db.scalar(select(Topic))
    assert client.get(f"/articles/{article.id}/entities").json()[0]["mentions"][1]["start_offset"] == 20
    assert client.get(f"/entities/{entity.id}").json()["article_count"] == 1
    assert client.get(f"/topics/{topic.id}").json()["article_count"] == 1
    assert client.get("/entities", params={"entity_type": "organization"}).json()["total"] == 1
    assert client.get("/search", params={"entity_id": str(entity.id)}).json()["total"] == 1
    assert client.get("/search", params={"topic": topic.slug}).json()["total"] == 1
