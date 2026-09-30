from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from sqlalchemy.orm import Session, aliased

from app.enums.source_dependency import (
    ArticleProvenanceReviewStatus,
    SourceRelationKind,
)
from app.models.source_dependency import ArticleProvenance, SourceRelation


class SourceDependencyRepository:
    def load_verified_article_provenance(
        self,
        db: Session,
        *,
        article_ids: list[UUID],
    ) -> list[ArticleProvenance]:
        if not article_ids:
            return []

        known_article_ids = set(article_ids)
        frontier = set(article_ids)
        by_id: dict[UUID, ArticleProvenance] = {}

        while frontier:
            statement = (
                select(ArticleProvenance)
                .where(
                    ArticleProvenance.article_id.in_(frontier),
                    ArticleProvenance.deleted_at.is_(None),
                    ArticleProvenance.review_status == ArticleProvenanceReviewStatus.VERIFIED,
                )
                .order_by(
                    ArticleProvenance.article_id,
                    ArticleProvenance.upstream_source_id,
                    ArticleProvenance.id,
                )
            )
            rows = list(db.scalars(statement).all())
            next_frontier: set[UUID] = set()

            for item in rows:
                by_id[item.id] = item
                if (
                    item.upstream_article_id is not None
                    and item.upstream_article_id not in known_article_ids
                ):
                    known_article_ids.add(item.upstream_article_id)
                    next_frontier.add(item.upstream_article_id)

            frontier = next_frontier

        return sorted(
            by_id.values(),
            key=lambda item: (
                str(item.article_id),
                str(item.upstream_source_id),
                str(item.upstream_article_id or ""),
                str(item.id),
            ),
        )

    def load_independence_relations(
        self,
        db: Session,
        *,
        seed_source_ids: set[UUID],
    ) -> list[SourceRelation]:
        if not seed_source_ids:
            return []

        kinds = (
            SourceRelationKind.EDITORIAL_PARENT,
            SourceRelationKind.SHARED_NEWSROOM,
            SourceRelationKind.JOINT_EDITORIAL_OPERATION,
        )
        known = set(seed_source_ids)
        frontier = set(seed_source_ids)
        by_id: dict[UUID, SourceRelation] = {}

        while frontier:
            statement = (
                select(SourceRelation)
                .where(
                    SourceRelation.deleted_at.is_(None),
                    SourceRelation.relation_kind.in_(kinds),
                    or_(
                        SourceRelation.source_id.in_(frontier),
                        SourceRelation.related_source_id.in_(frontier),
                    ),
                )
                .order_by(SourceRelation.id)
            )
            rows = list(db.scalars(statement).all())
            next_frontier: set[UUID] = set()

            for relation in rows:
                by_id[relation.id] = relation
                for source_id in (
                    relation.source_id,
                    relation.related_source_id,
                ):
                    if source_id not in known:
                        known.add(source_id)
                        next_frontier.add(source_id)

            frontier = next_frontier

        return sorted(
            by_id.values(),
            key=lambda item: str(item.id),
        )

    def get_active_article_source_id(
        self,
        db: Session,
        *,
        article_id: UUID,
    ) -> UUID | None:
        statement = (
            select(Source.id)
            .join(Feed, Feed.source_id == Source.id)
            .join(Article, Article.feed_id == Feed.id)
            .where(
                Article.id == article_id,
                Article.deleted_at.is_(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            )
            .limit(1)
        )
        return db.scalar(statement)

    def add_article_provenance(
        self,
        db: Session,
        provenance: ArticleProvenance,
    ) -> ArticleProvenance:
        db.add(provenance)
        return provenance

    def add_pending_article_provenance_candidate(
        self,
        db: Session,
        *,
        article_id: UUID,
        upstream_source_id: UUID,
        relation_kind,
        confidence: float,
        detection_method,
        notes: str | None,
    ) -> bool:
        statement = (
            insert(ArticleProvenance)
            .values(
                article_id=article_id,
                upstream_source_id=upstream_source_id,
                upstream_article_id=None,
                relation_kind=relation_kind,
                confidence=confidence,
                detection_method=detection_method,
                review_status=ArticleProvenanceReviewStatus.PENDING,
                reviewed_at=None,
                notes=notes,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    ArticleProvenance.article_id,
                    ArticleProvenance.upstream_source_id,
                    ArticleProvenance.upstream_article_id,
                    ArticleProvenance.relation_kind,
                ],
                index_where=ArticleProvenance.deleted_at.is_(None),
            )
            .returning(ArticleProvenance.id)
        )
        return db.scalar(statement) is not None

    def get_active_article_provenance(
        self,
        db: Session,
        *,
        article_id: UUID,
        provenance_id: UUID,
    ) -> ArticleProvenance | None:
        statement = select(ArticleProvenance).where(
            ArticleProvenance.id == provenance_id,
            ArticleProvenance.article_id == article_id,
            ArticleProvenance.deleted_at.is_(None),
        )
        return db.scalar(statement)

    def list_article_provenance(
        self,
        db: Session,
        *,
        article_id: UUID,
    ) -> list[ArticleProvenance]:
        statement = (
            select(ArticleProvenance)
            .where(
                ArticleProvenance.article_id == article_id,
                ArticleProvenance.deleted_at.is_(None),
            )
            .order_by(
                ArticleProvenance.review_status.desc(),
                ArticleProvenance.upstream_source_id,
                ArticleProvenance.id,
            )
        )
        return list(db.scalars(statement).all())


    def list_article_provenance_review_queue(
        self,
        db: Session,
        *,
        review_status: ArticleProvenanceReviewStatus,
        upstream_source_id: UUID | None,
        publisher_source_id: UUID | None,
        detection_method,
        relation_kind,
        min_confidence: float | None,
        created_from: datetime | None,
        limit: int,
        offset: int,
    ):
        publisher_source = aliased(Source)
        upstream_source = aliased(Source)

        conditions = [
            ArticleProvenance.deleted_at.is_(None),
            ArticleProvenance.review_status == review_status,
            Article.deleted_at.is_(None),
            Feed.deleted_at.is_(None),
            Feed.active.is_(True),
            publisher_source.deleted_at.is_(None),
            publisher_source.active.is_(True),
            upstream_source.deleted_at.is_(None),
            upstream_source.active.is_(True),
        ]
        if upstream_source_id is not None:
            conditions.append(
                ArticleProvenance.upstream_source_id == upstream_source_id
            )
        if publisher_source_id is not None:
            conditions.append(Feed.source_id == publisher_source_id)
        if detection_method is not None:
            conditions.append(
                ArticleProvenance.detection_method == detection_method
            )
        if relation_kind is not None:
            conditions.append(
                ArticleProvenance.relation_kind == relation_kind
            )
        if min_confidence is not None:
            conditions.append(
                ArticleProvenance.confidence >= min_confidence
            )
        if created_from is not None:
            conditions.append(
                ArticleProvenance.created_at >= created_from
            )

        count_statement = (
            select(func.count(ArticleProvenance.id))
            .select_from(ArticleProvenance)
            .join(Article, Article.id == ArticleProvenance.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .join(publisher_source, publisher_source.id == Feed.source_id)
            .join(
                upstream_source,
                upstream_source.id == ArticleProvenance.upstream_source_id,
            )
            .where(*conditions)
        )
        total = int(db.scalar(count_statement) or 0)

        statement = (
            select(
                ArticleProvenance,
                Article,
                publisher_source,
                upstream_source,
            )
            .join(Article, Article.id == ArticleProvenance.article_id)
            .join(Feed, Feed.id == Article.feed_id)
            .join(publisher_source, publisher_source.id == Feed.source_id)
            .join(
                upstream_source,
                upstream_source.id == ArticleProvenance.upstream_source_id,
            )
            .where(*conditions)
            .order_by(
                ArticleProvenance.created_at,
                ArticleProvenance.id,
            )
            .offset(offset)
            .limit(limit)
        )
        return total, list(db.execute(statement).all())
