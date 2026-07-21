from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.article import Article
from app.repositories.base import BaseRepository


class ArticleRepository(BaseRepository[Article]):
    def __init__(self) -> None:
        super().__init__(Article)

    def get_by_identity(
        self,
        db: Session,
        *,
        feed_id: UUID,
        identity_key: str,
    ) -> Article | None:
        statement = (
            select(Article)
            .where(Article.feed_id == feed_id)
            .where(Article.identity_key == identity_key)
            .where(Article.deleted_at.is_(None))
        )
        return db.scalar(statement)

    def get_by_guid(
        self,
        db: Session,
        *,
        feed_id: UUID,
        guid: str,
    ) -> Article | None:
        statement = (
            select(Article)
            .where(Article.feed_id == feed_id)
            .where(Article.guid == guid)
            .where(Article.deleted_at.is_(None))
            .limit(1)
        )
        return db.scalar(statement)

    def get_by_link(
        self,
        db: Session,
        *,
        feed_id: UUID,
        link: str,
    ) -> Article | None:
        statement = (
            select(Article)
            .where(Article.feed_id == feed_id)
            .where(Article.link == link)
            .where(Article.deleted_at.is_(None))
            .limit(1)
        )
        return db.scalar(statement)

    def list_by_feed(
        self,
        db: Session,
        feed_id: UUID,
    ) -> list[Article]:
        statement = (
            select(Article)
            .where(Article.feed_id == feed_id)
            .where(Article.deleted_at.is_(None))
            .order_by(
                Article.published_at.desc().nullslast(),
                Article.created_at.desc(),
            )
        )
        return list(db.scalars(statement).all())

    def list_pending_normalization(
        self,
        db: Session,
        *,
        normalization_version: int,
        limit: int,
    ) -> list[Article]:
        statement = (
            select(Article)
            .where(Article.deleted_at.is_(None))
            .where(
                (Article.normalization_version.is_(None))
                | (Article.normalization_version < normalization_version)
            )
            .order_by(Article.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(db.scalars(statement).all())
