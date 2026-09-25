from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationError
from app.models.article import Article
from app.repositories.article import ArticleRepository
from app.schemas.article_confirmation import ArticleConfirmationRoleUpdate


class ArticleConfirmationService:
    def __init__(
        self,
        repository: ArticleRepository | None = None,
    ) -> None:
        self.repository = repository or ArticleRepository()

    def get(
        self,
        db: Session,
        *,
        article_id: UUID,
    ) -> Article:
        article = self.repository.get_by_id(
            db,
            article_id,
        )
        if article is None:
            raise BusinessRuleViolationError(
                "Der Artikel existiert nicht oder ist nicht verfügbar."
            )
        return article

    def update(
        self,
        db: Session,
        *,
        article_id: UUID,
        data: ArticleConfirmationRoleUpdate,
    ) -> Article:
        article = self.get(
            db,
            article_id=article_id,
        )
        article.confirmation_role = data.confirmation_role
        self.repository.flush(db)
        return article
