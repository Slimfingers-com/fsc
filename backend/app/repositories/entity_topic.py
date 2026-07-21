from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.analysis.provider import EntityType
from app.models.article import Article
from app.models.entity import ArticleEntity, Entity, EntityAlias
from app.models.feed import Feed
from app.models.source import Source
from app.models.topic import ArticleTopic, Topic


class AmbiguousEntityAliasError(Exception):
    pass


class EntityTopicRepository:
    def find_entity(self, db: Session, normalized_name: str, entity_type: EntityType) -> Entity | None:
        canonical = db.scalar(select(Entity).where(Entity.normalized_name == normalized_name, Entity.entity_type == entity_type, Entity.deleted_at.is_(None)).limit(1))
        if canonical is not None:
            return canonical
        matches = list(db.scalars(select(Entity).join(EntityAlias).where(
            EntityAlias.normalized_alias == normalized_name, EntityAlias.entity_type == entity_type,
            EntityAlias.deleted_at.is_(None), Entity.deleted_at.is_(None),
        ).distinct().order_by(Entity.id).limit(2)).all())
        if len(matches) > 1:
            raise AmbiguousEntityAliasError(normalized_name)
        return matches[0] if matches else None

    def create_or_get_entity(self, db: Session, *, canonical_name: str, normalized_name: str, entity_type: EntityType) -> Entity:
        entity_id = db.scalar(insert(Entity).values(canonical_name=canonical_name, normalized_name=normalized_name, entity_type=entity_type).on_conflict_do_nothing().returning(Entity.id))
        entity = db.get(Entity, entity_id) if entity_id else db.scalar(select(Entity).where(Entity.normalized_name == normalized_name, Entity.entity_type == entity_type, Entity.deleted_at.is_(None)))
        if entity is None:
            raise RuntimeError("entity upsert conflict did not resolve to an active entity")
        db.execute(insert(EntityAlias).values(entity_id=entity.id, original_alias=canonical_name, normalized_alias=normalized_name, entity_type=entity_type).on_conflict_do_nothing())
        return entity

    def find_topic(self, db: Session, normalized_name: str) -> Topic | None:
        return db.scalar(select(Topic).where(Topic.normalized_name == normalized_name, Topic.deleted_at.is_(None)).limit(1))

    def create_or_get_topic(self, db: Session, *, name: str, normalized_name: str, slug: str, collision_slug: str) -> Topic:
        topic_id = db.scalar(insert(Topic).values(name=name, normalized_name=normalized_name, slug=slug).on_conflict_do_nothing().returning(Topic.id))
        topic = db.get(Topic, topic_id) if topic_id else self.find_topic(db, normalized_name)
        if topic is not None:
            return topic
        topic_id = db.scalar(insert(Topic).values(name=name, normalized_name=normalized_name, slug=collision_slug).on_conflict_do_nothing().returning(Topic.id))
        topic = db.get(Topic, topic_id) if topic_id else self.find_topic(db, normalized_name)
        if topic is None:
            raise RuntimeError("topic upsert conflict did not resolve to an active topic")
        return topic

    def replace_article_results(self, db: Session, article_id: UUID) -> None:
        db.execute(delete(ArticleEntity).where(ArticleEntity.article_id == article_id))
        db.execute(delete(ArticleTopic).where(ArticleTopic.article_id == article_id))

    @staticmethod
    def _pending_conditions(*, provider: str, version: str, config_version: str, now: datetime):
        return (
            Article.deleted_at.is_(None), Article.normalized_at.is_not(None), Article.normalized_text.is_not(None),
            Feed.deleted_at.is_(None), Feed.active.is_(True), Source.deleted_at.is_(None), Source.active.is_(True),
            or_(Article.entity_topic_retry_after.is_(None), Article.entity_topic_retry_after <= now),
            or_(Article.entity_topic_claim_expires_at.is_(None), Article.entity_topic_claim_expires_at <= now),
            or_(
                Article.entity_topic_analysis_content_hash.is_distinct_from(Article.content_hash),
                Article.entity_topic_analysis_normalization_version.is_distinct_from(Article.normalization_version),
                Article.entity_topic_analysis_provider.is_distinct_from(provider),
                Article.entity_topic_analysis_version.is_distinct_from(version),
                Article.entity_topic_analysis_config_version.is_distinct_from(config_version),
            ),
        )

    def list_pending_articles(self, db: Session, *, provider: str, version: str, config_version: str, limit: int, now: datetime) -> list[Article]:
        return list(db.scalars(select(Article).join(Feed).join(Source).where(
            *self._pending_conditions(provider=provider, version=version, config_version=config_version, now=now),
        ).order_by(Article.created_at, Article.id).limit(limit)).all())

    def claim_pending_articles(self, db: Session, *, provider: str, version: str, config_version: str, limit: int, now: datetime, claim_expires_at: datetime, claimed_by: str) -> list[UUID]:
        ids = list(db.scalars(select(Article.id).join(Feed).join(Source).where(
            *self._pending_conditions(provider=provider, version=version, config_version=config_version, now=now),
        ).order_by(Article.created_at, Article.id).limit(limit).with_for_update(skip_locked=True)).all())
        if ids:
            db.execute(update(Article).where(Article.id.in_(ids)).values(entity_topic_claimed_at=now, entity_topic_claimed_by=claimed_by, entity_topic_claim_expires_at=claim_expires_at))
        return ids

    def list_entities(self, db: Session, *, query: str | None, entity_type: EntityType | None, offset: int, limit: int) -> tuple[list[Entity], int]:
        conditions: list[ColumnElement[bool]] = [Entity.deleted_at.is_(None)]
        if query:
            conditions.append(Entity.normalized_name.ilike(f"%{query}%"))
        if entity_type:
            conditions.append(Entity.entity_type == entity_type)
        total = db.scalar(select(func.count()).select_from(Entity).where(*conditions)) or 0
        items = list(db.scalars(select(Entity).options(selectinload(Entity.aliases)).where(*conditions).order_by(Entity.normalized_name, Entity.id).offset(offset).limit(limit)).all())
        return items, total

    def list_topics(self, db: Session, *, query: str | None, offset: int, limit: int) -> tuple[list[Topic], int]:
        conditions: list[ColumnElement[bool]] = [Topic.deleted_at.is_(None)]
        if query:
            conditions.append(Topic.normalized_name.ilike(f"%{query}%"))
        total = db.scalar(select(func.count()).select_from(Topic).where(*conditions)) or 0
        items = list(db.scalars(select(Topic).where(*conditions).order_by(Topic.normalized_name, Topic.id).offset(offset).limit(limit)).all())
        return items, total

    def get_entity(self, db: Session, entity_id: UUID) -> Entity | None:
        return db.scalar(select(Entity).options(selectinload(Entity.aliases)).where(Entity.id == entity_id, Entity.deleted_at.is_(None)))

    def get_topic(self, db: Session, topic_id: UUID) -> Topic | None:
        return db.scalar(select(Topic).where(Topic.id == topic_id, Topic.deleted_at.is_(None)))
