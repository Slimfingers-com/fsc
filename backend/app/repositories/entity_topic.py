from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.analysis.provider import EntityType
from app.models.entity import ArticleEntity, Entity, EntityAlias
from app.models.topic import ArticleTopic, Topic


class AmbiguousEntityAliasError(Exception):
    pass


class EntityTopicRepository:
    def find_entity(
        self,
        db: Session,
        normalized_name: str,
        entity_type: EntityType,
    ) -> Entity | None:
        canonical = db.scalar(
            select(Entity)
            .where(
                Entity.normalized_name == normalized_name,
                Entity.entity_type == entity_type,
                Entity.deleted_at.is_(None),
            )
            .limit(1)
        )

        if canonical is not None:
            return canonical

        matches = list(
            db.scalars(
                select(Entity)
                .join(EntityAlias)
                .where(
                    EntityAlias.normalized_alias == normalized_name,
                    EntityAlias.entity_type == entity_type,
                    EntityAlias.deleted_at.is_(None),
                    Entity.deleted_at.is_(None),
                )
                .distinct()
                .order_by(Entity.id)
                .limit(2)
            ).all()
        )

        if len(matches) > 1:
            raise AmbiguousEntityAliasError(
                normalized_name
            )

        return matches[0] if matches else None

    def create_or_get_entity(
        self,
        db: Session,
        *,
        canonical_name: str,
        normalized_name: str,
        entity_type: EntityType,
    ) -> Entity:
        entity_id = db.scalar(
            insert(Entity)
            .values(
                canonical_name=canonical_name,
                normalized_name=normalized_name,
                entity_type=entity_type,
            )
            .on_conflict_do_nothing()
            .returning(Entity.id)
        )

        if entity_id is not None:
            entity = db.get(
                Entity,
                entity_id,
            )
        else:
            entity = db.scalar(
                select(Entity).where(
                    Entity.normalized_name == normalized_name,
                    Entity.entity_type == entity_type,
                    Entity.deleted_at.is_(None),
                )
            )

        if entity is None:
            raise RuntimeError(
                "entity upsert conflict did not resolve to an active entity"
            )

        db.execute(
            insert(EntityAlias)
            .values(
                entity_id=entity.id,
                original_alias=canonical_name,
                normalized_alias=normalized_name,
                entity_type=entity_type,
            )
            .on_conflict_do_nothing()
        )

        return entity

    def find_topic(
        self,
        db: Session,
        normalized_name: str,
    ) -> Topic | None:
        return db.scalar(
            select(Topic)
            .where(
                Topic.normalized_name == normalized_name,
                Topic.deleted_at.is_(None),
            )
            .limit(1)
        )

    def create_or_get_topic(
        self,
        db: Session,
        *,
        name: str,
        normalized_name: str,
        slug: str,
        collision_slug: str,
    ) -> Topic:
        topic_id = db.scalar(
            insert(Topic)
            .values(
                name=name,
                normalized_name=normalized_name,
                slug=slug,
            )
            .on_conflict_do_nothing()
            .returning(Topic.id)
        )

        if topic_id is not None:
            topic = db.get(
                Topic,
                topic_id,
            )
        else:
            topic = self.find_topic(
                db,
                normalized_name,
            )

        if topic is not None:
            return topic

        topic_id = db.scalar(
            insert(Topic)
            .values(
                name=name,
                normalized_name=normalized_name,
                slug=collision_slug,
            )
            .on_conflict_do_nothing()
            .returning(Topic.id)
        )

        if topic_id is not None:
            topic = db.get(
                Topic,
                topic_id,
            )
        else:
            topic = self.find_topic(
                db,
                normalized_name,
            )

        if topic is None:
            raise RuntimeError(
                "topic upsert conflict did not resolve to an active topic"
            )

        return topic

    def replace_article_results(
        self,
        db: Session,
        article_id: UUID,
    ) -> None:
        db.execute(
            delete(ArticleEntity).where(
                ArticleEntity.article_id == article_id
            )
        )

        db.execute(
            delete(ArticleTopic).where(
                ArticleTopic.article_id == article_id
            )
        )

    def list_entities(
        self,
        db: Session,
        *,
        query: str | None,
        entity_type: EntityType | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Entity], int]:
        conditions: list[ColumnElement[bool]] = [
            Entity.deleted_at.is_(None)
        ]

        if query:
            conditions.append(
                Entity.normalized_name.ilike(
                    f"%{query}%"
                )
            )

        if entity_type:
            conditions.append(
                Entity.entity_type == entity_type
            )

        total = (
            db.scalar(
                select(func.count())
                .select_from(Entity)
                .where(*conditions)
            )
            or 0
        )

        items = list(
            db.scalars(
                select(Entity)
                .options(
                    selectinload(Entity.aliases)
                )
                .where(*conditions)
                .order_by(
                    Entity.normalized_name,
                    Entity.id,
                )
                .offset(offset)
                .limit(limit)
            ).all()
        )

        return items, total

    def list_topics(
        self,
        db: Session,
        *,
        query: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Topic], int]:
        conditions: list[ColumnElement[bool]] = [
            Topic.deleted_at.is_(None)
        ]

        if query:
            conditions.append(
                Topic.normalized_name.ilike(
                    f"%{query}%"
                )
            )

        total = (
            db.scalar(
                select(func.count())
                .select_from(Topic)
                .where(*conditions)
            )
            or 0
        )

        items = list(
            db.scalars(
                select(Topic)
                .where(*conditions)
                .order_by(
                    Topic.normalized_name,
                    Topic.id,
                )
                .offset(offset)
                .limit(limit)
            ).all()
        )

        return items, total

    def get_entity(
        self,
        db: Session,
        entity_id: UUID,
    ) -> Entity | None:
        return db.scalar(
            select(Entity)
            .options(
                selectinload(Entity.aliases)
            )
            .where(
                Entity.id == entity_id,
                Entity.deleted_at.is_(None),
            )
        )

    def get_topic(
        self,
        db: Session,
        topic_id: UUID,
    ) -> Topic | None:
        return db.scalar(
            select(Topic).where(
                Topic.id == topic_id,
                Topic.deleted_at.is_(None),
            )
        )