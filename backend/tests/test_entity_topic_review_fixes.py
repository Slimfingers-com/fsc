from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.analysis.provider import EntityMentionResult, EntityType, TextPart, TopicResult
from app.analysis.resolver import EntityResolver, TopicResolver
from app.enums.article_identity_type import ArticleIdentityType
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.entity import ArticleEntity, Entity, EntityAlias
from app.models.topic import Topic
from app.models.feed import Feed
from app.models.source import Source
from app.repositories.entity_topic import EntityTopicRepository
from app.services.entity_topic_analysis import EntityTopicAnalysisService
from tests.conftest import TestSessionLocal


def make_articles(db, count: int) -> list[Article]:
    token = uuid4().hex
    source = Source(name=token, normalized_name=token, slug=token, url=f"https://{token}.test", source_type=SourceType.NEWS)
    feed = Feed(source=source, name="Main", url=f"https://{token}.test/feed")
    now = datetime.now(UTC)
    articles = [Article(feed=feed, identity_type=ArticleIdentityType.DERIVED, identity_key=f"{index:064d}", normalized_title=f"Title {index}", normalized_text=f"Body {index}", language_code="en", content_hash=f"{index:064x}", normalization_version=1, normalized_at=now, created_at=now + timedelta(microseconds=index)) for index in range(count)]
    db.add_all(articles)
    db.flush()
    return articles


def mark_current(article: Article, service: EntityTopicAnalysisService) -> None:
    article.entity_topic_analysis_content_hash = article.content_hash
    article.entity_topic_analysis_normalization_version = article.normalization_version
    article.entity_topic_analysis_provider = service.analyzer.provider
    article.entity_topic_analysis_version = service.analyzer.version
    article.entity_topic_analysis_config_version = service.config_version


def test_current_prefix_cannot_starve_later_pending_articles(db):
    service = EntityTopicAnalysisService()
    articles = make_articles(db, 10)
    for article in articles[:9]:
        mark_current(article, service)
    db.flush()
    selected = service.repository.list_pending_articles(db, provider=service.analyzer.provider, version=service.analyzer.version, config_version=service.config_version, limit=1)
    assert [article.id for article in selected] == [articles[9].id]


def test_more_than_four_batches_are_eventually_reachable(db):
    service = EntityTopicAnalysisService()
    articles = make_articles(db, 9)
    reached = []
    for _ in articles:
        selected = service.repository.list_pending_articles(db, provider=service.analyzer.provider, version=service.analyzer.version, config_version=service.config_version, limit=1)
        assert len(selected) == 1
        reached.append(selected[0].id)
        mark_current(selected[0], service)
        db.flush()
    assert reached == [article.id for article in articles]
    assert service.repository.list_pending_articles(db, provider=service.analyzer.provider, version=service.analyzer.version, config_version=service.config_version, limit=1) == []


def test_content_and_analyzer_identity_control_pending_state(db):
    service = EntityTopicAnalysisService()
    article = make_articles(db, 1)[0]
    mark_current(article, service)
    db.flush()
    assert service.repository.list_pending_articles(db, provider=service.analyzer.provider, version=service.analyzer.version, config_version=service.config_version, limit=1) == []
    article.content_hash = "f" * 64
    db.flush()
    assert service.repository.list_pending_articles(db, provider=service.analyzer.provider, version=service.analyzer.version, config_version=service.config_version, limit=1) == [article]
    mark_current(article, service)
    db.flush()
    assert service.repository.list_pending_articles(db, provider=service.analyzer.provider, version="next", config_version=service.config_version, limit=1) == [article]


def test_ambiguous_and_soft_deleted_aliases_are_not_arbitrarily_reused(db):
    alias = f"shared-{uuid4().hex}"
    entities = [Entity(canonical_name=f"Entity {index}", normalized_name=f"entity-{uuid4().hex}", entity_type=EntityType.ORGANIZATION) for index in range(2)]
    db.add_all(entities)
    db.flush()
    db.add_all([EntityAlias(entity_id=entity.id, original_alias=alias, normalized_alias=alias, entity_type=EntityType.ORGANIZATION) for entity in entities])
    db.flush()
    result = EntityMentionResult(alias, alias, EntityType.ORGANIZATION, .99, .9, TextPart.BODY)
    assert EntityResolver().resolve(db, result) is None
    entities[1].deleted_at = datetime.now(UTC)
    db.flush()
    assert EntityResolver().resolve(db, result).id == entities[0].id


def _concurrent_resolve(kind: str) -> list:
    normalized = f"concurrent-{uuid4().hex}"
    barrier = Barrier(2)
    def resolve():
        with TestSessionLocal() as session:
            barrier.wait()
            with session.begin():
                if kind == "entity":
                    value = EntityResolver().resolve(session, EntityMentionResult(normalized, normalized, EntityType.ORGANIZATION, .99, .9, TextPart.BODY))
                else:
                    value = TopicResolver().resolve(session, TopicResult(normalized, .9, .99))
                return value.id
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _: resolve(), range(2)))
    with TestSessionLocal.begin() as session:
        session.execute(delete(Entity if kind == "entity" else Topic).where((Entity.id if kind == "entity" else Topic.id).in_(ids)))
    return ids


@pytest.mark.parametrize("kind", ["entity", "topic"])
def test_concurrent_resolution_returns_one_record_without_integrity_error(kind):
    ids = _concurrent_resolve(kind)
    assert ids[0] == ids[1]


def test_unicode_slug_collisions_do_not_merge_different_topics(db):
    resolver = TopicResolver()
    first = resolver.resolve(db, TopicResult("café policy", .9, .99))
    second = resolver.resolve(db, TopicResult("cafe policy", .9, .99))
    assert first.id != second.id
    assert first.slug != second.slug


def test_offset_constraints_are_database_enforced(db):
    article = make_articles(db, 1)[0]
    entity = Entity(canonical_name="Constraint", normalized_name=f"constraint-{uuid4().hex}", entity_type=EntityType.OTHER)
    db.add(entity)
    db.flush()
    invalid = ArticleEntity(article_id=article.id, entity_id=entity.id, mention_text="x", normalized_mention="x", entity_type=entity.entity_type, text_part=TextPart.BODY, start_offset=2, end_offset=1, confidence=.9, salience=.9, extraction_provider="test", extraction_version="1")
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(invalid)
        db.flush()
