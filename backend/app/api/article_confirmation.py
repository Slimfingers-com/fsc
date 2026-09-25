from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.sources import require_source_admin
from app.db.session import get_db
from app.schemas.article_confirmation import (
    ArticleConfirmationRoleRead,
    ArticleConfirmationRoleUpdate,
)
from app.services.article_confirmation import ArticleConfirmationService


router = APIRouter(
    prefix="/articles",
    tags=["article-confirmation"],
)

service = ArticleConfirmationService()


def _read(article) -> ArticleConfirmationRoleRead:
    return ArticleConfirmationRoleRead(
        article_id=article.id,
        confirmation_role=article.confirmation_role,
    )


@router.get(
    "/{article_id}/confirmation-role",
    response_model=ArticleConfirmationRoleRead,
)
def get_article_confirmation_role(
    article_id: UUID,
    db: Session = Depends(get_db),
):
    return _read(
        service.get(
            db,
            article_id=article_id,
        )
    )


@router.patch(
    "/{article_id}/confirmation-role",
    response_model=ArticleConfirmationRoleRead,
)
def update_article_confirmation_role(
    article_id: UUID,
    data: ArticleConfirmationRoleUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_source_admin),
):
    article = service.update(
        db,
        article_id=article_id,
        data=data,
    )
    db.commit()
    db.refresh(article)
    return _read(article)
