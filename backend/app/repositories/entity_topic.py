from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.analysis.provider import EntityType
from app.models.article import Article
from app.models.entity import ArticleEntity, Entity
from app.models.feed import Feed
from app.models.source import Source
from app.models.topic import ArticleTopic, Topic
from app.analysis.normalization import normalize_name


class EntityTopicRepository:
    def find_entity(self, db: Session, normalized_name: str, entity_type: EntityType) -> Entity | None:
        entities = db.scalars(select(Entity).where(Entity.entity_type == entity_type, Entity.deleted_at.is_(None)).order_by(Entity.created_at, Entity.id)).all()
        return next((entity for entity in entities if entity.normalized_name == normalized_name or normalized_name in {normalize_name(alias) for alias in entity.aliases}), None)

    def find_topic(self, db: Session, normalized_name: str) -> Topic | None:
        return db.scalar(select(Topic).where(Topic.normalized_name == normalized_name, Topic.deleted_at.is_(None)).limit(1))

    def replace_article_results(self, db: Session, article_id: UUID) -> None:
        db.execute(delete(ArticleEntity).where(ArticleEntity.article_id == article_id))
        db.execute(delete(ArticleTopic).where(ArticleTopic.article_id == article_id))

    def list_pending_articles(self, db: Session, *, analysis_hash_for, limit: int) -> list[Article]:
        candidates = list(db.scalars(select(Article).join(Feed).join(Source).where(
            Article.deleted_at.is_(None), Article.normalized_at.is_not(None), Article.normalized_text.is_not(None),
            Feed.deleted_at.is_(None), Feed.active.is_(True), Source.deleted_at.is_(None), Source.active.is_(True),
        ).order_by(Article.created_at, Article.id).limit(limit * 4).with_for_update(skip_locked=True)).all())
        return [article for article in candidates if article.entity_topic_analysis_hash != analysis_hash_for(article)][:limit]

    def list_entities(self, db: Session, *, query: str | None, entity_type: EntityType | None, offset: int, limit: int) -> tuple[list[Entity], int]:
        conditions = [Entity.deleted_at.is_(None)]
        if query:
            conditions.append(Entity.normalized_name.ilike(f"%{query}%"))
        if entity_type:
            conditions.append(Entity.entity_type == entity_type)
        total = db.scalar(select(func.count()).select_from(Entity).where(*conditions)) or 0
        items = list(db.scalars(select(Entity).where(*conditions).order_by(Entity.normalized_name, Entity.id).offset(offset).limit(limit)).all())
        return items, total

    def list_topics(self, db: Session, *, query: str | None, offset: int, limit: int) -> tuple[list[Topic], int]:
        conditions = [Topic.deleted_at.is_(None)]
        if query:
            conditions.append(Topic.normalized_name.ilike(f"%{query}%"))
        total = db.scalar(select(func.count()).select_from(Topic).where(*conditions)) or 0
        items = list(db.scalars(select(Topic).where(*conditions).order_by(Topic.normalized_name, Topic.id).offset(offset).limit(limit)).all())
        return items, total

    def get_entity(self, db: Session, entity_id: UUID) -> Entity | None:
        return db.scalar(select(Entity).where(Entity.id == entity_id, Entity.deleted_at.is_(None)))

    def get_topic(self, db: Session, topic_id: UUID) -> Topic | None:
        return db.scalar(select(Topic).where(Topic.id == topic_id, Topic.deleted_at.is_(None)))
