from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.source import Source
from app.repositories.base import BaseRepository


class SourceRepository(BaseRepository[Source]):
    def __init__(self) -> None:
        super().__init__(Source)

    def get_by_slug(
        self,
        db: Session,
        slug: str,
    ) -> Source | None:
        statement = (
            select(Source)
            .options(selectinload(Source.feeds))
            .where(Source.slug == slug)
            .where(Source.deleted_at.is_(None))
        )

        return db.scalar(statement)

    def get_by_normalized_name(
        self,
        db: Session,
        normalized_name: str,
    ) -> Source | None:
        statement = (
            select(Source)
            .where(Source.normalized_name == normalized_name)
            .where(Source.deleted_at.is_(None))
        )

        return db.scalar(statement)

    def exists_by_normalized_name(
        self,
        db: Session,
        normalized_name: str,
    ) -> bool:
        statement = (
            select(Source.id)
            .where(Source.normalized_name == normalized_name)
            .where(Source.deleted_at.is_(None))
            .limit(1)
        )

        return db.scalar(statement) is not None

    def exists_by_slug(
        self,
        db: Session,
        slug: str,
    ) -> bool:
        statement = (
            select(Source.id)
            .where(Source.slug == slug)
            .where(Source.deleted_at.is_(None))
            .limit(1)
        )

        return db.scalar(statement) is not None

    def list_active(
        self,
        db: Session,
    ) -> list[Source]:
        statement = (
            select(Source)
            .options(selectinload(Source.feeds))
            .where(Source.active.is_(True))
            .where(Source.deleted_at.is_(None))
            .order_by(Source.name)
        )

        return list(db.scalars(statement).all())
