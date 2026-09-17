from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.feed import Feed
from app.models.search_document import SearchDocument
from app.models.source import Source
from app.repositories.base import BaseRepository


class SearchDocumentRepository(BaseRepository[SearchDocument]):
    def __init__(self) -> None:
        super().__init__(SearchDocument)

    def get_by_article_id(
        self,
        db: Session,
        article_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> SearchDocument | None:
        statement = select(SearchDocument).where(
            SearchDocument.article_id == article_id
        )

        if not include_deleted:
            statement = statement.where(
                SearchDocument.deleted_at.is_(None)
            )

        return db.scalar(statement)

    def hard_delete(
        self,
        db: Session,
        document: SearchDocument,
    ) -> None:
        db.delete(document)

    def delete_ineligible(
        self,
        db: Session,
    ) -> list[UUID]:
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

        statement = (
            delete(SearchDocument)
            .where(
                or_(
                    SearchDocument.deleted_at.is_not(None),
                    ~eligible_article,
                )
            )
            .returning(SearchDocument.article_id)
        )

        return list(
            db.scalars(statement).all()
        )