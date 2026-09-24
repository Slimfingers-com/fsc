from uuid import UUID

from sqlalchemy import or_, select

from app.models.article import Article
from app.models.feed import Feed
from app.models.source import Source
from sqlalchemy.orm import Session

from app.enums.source_dependency import SourceRelationKind
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
        statement = (
            select(ArticleProvenance)
            .where(
                ArticleProvenance.article_id.in_(article_ids),
                ArticleProvenance.deleted_at.is_(None),
                ArticleProvenance.verified.is_(True),
            )
            .order_by(
                ArticleProvenance.article_id,
                ArticleProvenance.upstream_source_id,
                ArticleProvenance.id,
            )
        )
        return list(db.scalars(statement).all())

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
                ArticleProvenance.verified.desc(),
                ArticleProvenance.upstream_source_id,
                ArticleProvenance.id,
            )
        )
        return list(db.scalars(statement).all())
