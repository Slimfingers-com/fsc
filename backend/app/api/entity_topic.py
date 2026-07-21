from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.analysis.normalization import normalize_name, normalize_topic
from app.analysis.provider import EntityType
from app.db.session import get_db
from app.models.article import Article
from app.models.entity import ArticleEntity
from app.models.feed import Feed
from app.models.source import Source
from app.models.topic import ArticleTopic
from app.repositories.entity_topic import EntityTopicRepository
from app.schemas.entity_topic import ArticleEntityRead, ArticleTopicRead, EntityDetailRead, EntityRead, LinkedArticleRead, MentionRead, PageRead, TopicDetailRead, TopicRead

router = APIRouter(tags=["entity-topic"])
repository = EntityTopicRepository()


def _active_article_conditions():
    return (Article.deleted_at.is_(None), Feed.deleted_at.is_(None), Feed.active.is_(True), Source.deleted_at.is_(None), Source.active.is_(True))


def _entity_read(entity) -> EntityRead:
    return EntityRead(id=entity.id, canonical_name=entity.canonical_name, normalized_name=entity.normalized_name, entity_type=entity.entity_type, description=entity.description, aliases=[alias.original_alias for alias in entity.aliases if alias.deleted_at is None and alias.normalized_alias != entity.normalized_name], external_ids=entity.external_ids)


@router.get("/articles/{article_id}/entities", response_model=list[ArticleEntityRead])
def article_entities(article_id: UUID, db: Session = Depends(get_db)):
    rows = db.execute(select(ArticleEntity).options(selectinload(ArticleEntity.entity)).join(Article).join(Feed).join(Source).where(Article.id == article_id, *_active_article_conditions()).order_by(ArticleEntity.entity_id, ArticleEntity.start_offset.nullslast(), ArticleEntity.id)).scalars().all()
    if not rows and not db.scalar(select(Article.id).join(Feed).join(Source).where(Article.id == article_id, *_active_article_conditions())):
        raise HTTPException(404, "Article not found")
    grouped: dict[UUID, ArticleEntityRead] = {}
    for row in rows:
        grouped.setdefault(row.entity_id, ArticleEntityRead(id=row.entity.id, canonical_name=row.entity.canonical_name, entity_type=row.entity_type, mentions=[])).mentions.append(MentionRead.model_validate(row))
    return list(grouped.values())


@router.get("/articles/{article_id}/topics", response_model=list[ArticleTopicRead])
def article_topics(article_id: UUID, db: Session = Depends(get_db)):
    rows = db.scalars(select(ArticleTopic).options(selectinload(ArticleTopic.topic)).join(Article).join(Feed).join(Source).where(Article.id == article_id, *_active_article_conditions()).order_by(ArticleTopic.relevance.desc(), ArticleTopic.topic_id)).all()
    if not rows and not db.scalar(select(Article.id).join(Feed).join(Source).where(Article.id == article_id, *_active_article_conditions())):
        raise HTTPException(404, "Article not found")
    return [ArticleTopicRead(id=row.topic.id, name=row.topic.name, slug=row.topic.slug, relevance=row.relevance, confidence=row.confidence) for row in rows]


@router.get("/entities", response_model=PageRead)
def entities(query: Annotated[str | None, Query(max_length=500)] = None, entity_type: EntityType | None = None, page: Annotated[int, Query(ge=1)] = 1, page_size: Annotated[int, Query(ge=1, le=100)] = 20, db: Session = Depends(get_db)):
    items, total = repository.list_entities(db, query=normalize_name(query) if query else None, entity_type=entity_type, offset=(page - 1) * page_size, limit=page_size)
    return PageRead(items=[_entity_read(item) for item in items], total=total, page=page, page_size=page_size, pages=ceil(total/page_size) if total else 0)


@router.get("/topics", response_model=PageRead)
def topics(query: Annotated[str | None, Query(max_length=500)] = None, page: Annotated[int, Query(ge=1)] = 1, page_size: Annotated[int, Query(ge=1, le=100)] = 20, db: Session = Depends(get_db)):
    items, total = repository.list_topics(db, query=normalize_topic(query) if query else None, offset=(page - 1) * page_size, limit=page_size)
    return PageRead(items=[TopicRead.model_validate(item) for item in items], total=total, page=page, page_size=page_size, pages=ceil(total/page_size) if total else 0)


def _latest(db: Session, relation, id_column, object_id: UUID):
    statement = select(Article).join(relation).join(Feed).join(Source).where(id_column == object_id, *_active_article_conditions()).order_by(Article.published_at.desc().nullslast(), Article.id).limit(10)
    articles = list(db.scalars(statement).unique().all())
    count = db.scalar(select(func.count(func.distinct(Article.id))).select_from(Article).join(relation).join(Feed).join(Source).where(id_column == object_id, *_active_article_conditions())) or 0
    return count, [LinkedArticleRead(id=a.id, title=a.normalized_title or a.title, published_at=a.published_at) for a in articles]


@router.get("/entities/{entity_id}", response_model=EntityDetailRead)
def entity_detail(entity_id: UUID, db: Session = Depends(get_db)):
    entity = repository.get_entity(db, entity_id)
    if entity is None:
        raise HTTPException(404, "Entity not found")
    count, latest = _latest(db, ArticleEntity, ArticleEntity.entity_id, entity_id)
    return EntityDetailRead(**_entity_read(entity).model_dump(), article_count=count, latest_articles=latest)


@router.get("/topics/{topic_id}", response_model=TopicDetailRead)
def topic_detail(topic_id: UUID, db: Session = Depends(get_db)):
    topic = repository.get_topic(db, topic_id)
    if topic is None:
        raise HTTPException(404, "Topic not found")
    count, latest = _latest(db, ArticleTopic, ArticleTopic.topic_id, topic_id)
    return TopicDetailRead(**TopicRead.model_validate(topic).model_dump(), article_count=count, latest_articles=latest)
