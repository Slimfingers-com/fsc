from uuid import UUID
from typing import cast

from sqlalchemy import delete, func, or_, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, joinedload

from app.models.article import Article
from app.models.feed import Feed
from app.models.search_document import SearchDocument
from app.models.source import Source
from app.repositories.base import BaseRepository


class SearchDocumentRepository(BaseRepository[SearchDocument]):
    def __init__(self) -> None:
        super().__init__(SearchDocument)

    def get_by_article_id(
        self, db: Session, article_id: UUID, *, include_deleted: bool = False
    ) -> SearchDocument | None:
        statement = select(SearchDocument).where(SearchDocument.article_id == article_id)
        if not include_deleted:
            statement = statement.where(SearchDocument.deleted_at.is_(None))
        return db.scalar(statement)

    def hard_delete(self, db: Session, document: SearchDocument) -> None:
        db.delete(document)

    def delete_ineligible(self, db: Session) -> int:
        eligible_article = (
            select(Article.id)
            .join(Article.feed)
            .join(Feed.source)
            .where(
                Article.id == SearchDocument.article_id,
                Article.deleted_at.is_(None),
                Feed.deleted_at.is_(None),
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
            )
            .exists()
        )
        result = db.execute(
            delete(SearchDocument).where(
                or_(SearchDocument.deleted_at.is_not(None), ~eligible_article)
            )
        )
        return cast(CursorResult, result).rowcount or 0

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
                Feed.active.is_(True),
                Source.deleted_at.is_(None),
                Source.active.is_(True),
                or_(
                    SearchDocument.id.is_(None),
                    SearchDocument.deleted_at.is_not(None),
                    SearchDocument.source_id.is_distinct_from(Source.id),
                    SearchDocument.source_name.is_distinct_from(Source.name),
                    SearchDocument.source_slug.is_distinct_from(Source.slug),
                    SearchDocument.title.is_distinct_from(func.coalesce(Article.normalized_title, "")),
                    SearchDocument.body.is_distinct_from(func.coalesce(Article.normalized_text, "")),
                    SearchDocument.url.is_distinct_from(Article.link),
                    SearchDocument.language_code.is_distinct_from(Article.language_code),
                    SearchDocument.published_at.is_distinct_from(Article.published_at),
                    SearchDocument.builder_version < builder_version,
                ),
            )
            .options(joinedload(Article.feed).joinedload(Feed.source))
            .order_by(Article.normalized_at.asc(), Article.id.asc())
            .limit(limit)
            .with_for_update(of=Article, skip_locked=True)
        )
        return list(db.scalars(statement).unique().all())
