from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.article import Article
from app.models.feed import Feed
from app.models.search_document import SearchDocument
from app.models.source import Source
from app.repositories.base import BaseRepository


class SearchDocumentRepository(BaseRepository[SearchDocument]):
    def __init__(self) -> None:
        super().__init__(SearchDocument)

    def get_by_article_id(self, db: Session, article_id: UUID) -> SearchDocument | None:
        statement = select(SearchDocument).where(
            SearchDocument.article_id == article_id,
            SearchDocument.deleted_at.is_(None),
        )
        return db.scalar(statement)

    def list_pending_articles(self, db: Session, *, builder_version: int, limit: int) -> list[Article]:
        statement = (
            select(Article)
            .join(Article.feed)
            .join(Feed.source)
            .outerjoin(SearchDocument, SearchDocument.article_id == Article.id)
            .where(
                Article.deleted_at.is_(None),
                Article.normalized_at.is_not(None),
                Feed.deleted_at.is_(None),
                Source.deleted_at.is_(None),
                or_(
                    SearchDocument.id.is_(None),
                    SearchDocument.content_hash.is_distinct_from(Article.content_hash),
                    SearchDocument.builder_version < builder_version,
                ),
            )
            .options(joinedload(Article.feed).joinedload(Feed.source))
            .order_by(Article.normalized_at.asc(), Article.id.asc())
            .limit(limit)
            .with_for_update(of=Article, skip_locked=True)
        )
        return list(db.scalars(statement).unique().all())
