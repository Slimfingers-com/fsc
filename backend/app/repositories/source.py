from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.feed import Feed
from app.models.source import Source
from app.models.source_metadata import (
    SourceClassification,
    SourceMetric,
    SourceOutlet,
)
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
            .options(
                selectinload(
                    Source.feeds.and_(
                        Feed.deleted_at.is_(None)
                    )
                ),
                selectinload(
                    Source.outlets.and_(
                        SourceOutlet.deleted_at.is_(None)
                    )
                ),
                selectinload(
                    Source.classifications.and_(
                        SourceClassification.deleted_at.is_(None)
                    )
                ),
                selectinload(
                    Source.metrics.and_(
                        SourceMetric.deleted_at.is_(None)
                    )
                ),
            )
            .execution_options(
                populate_existing=True
            )
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
            .options(
                selectinload(
                    Source.feeds.and_(
                        Feed.deleted_at.is_(None)
                    )
                )
            )
            .execution_options(
                populate_existing=True
            )
            .where(Source.active.is_(True))
            .where(Source.deleted_at.is_(None))
            .order_by(Source.name)
        )

        return list(db.scalars(statement).all())

    def get_active_outlet(
        self,
        db: Session,
        outlet_id: UUID,
    ) -> SourceOutlet | None:
        statement = (
            select(SourceOutlet)
            .where(SourceOutlet.id == outlet_id)
            .where(SourceOutlet.deleted_at.is_(None))
            .where(SourceOutlet.active.is_(True))
        )
        return db.scalar(statement)

    def add_outlet(
        self,
        db: Session,
        outlet: SourceOutlet,
    ) -> SourceOutlet:
        db.add(outlet)
        return outlet

    def add_classification(
        self,
        db: Session,
        classification: SourceClassification,
    ) -> SourceClassification:
        db.add(classification)
        return classification

    def add_metric(
        self,
        db: Session,
        metric: SourceMetric,
    ) -> SourceMetric:
        db.add(metric)
        return metric
