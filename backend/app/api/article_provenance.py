from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.sources import require_source_admin
from app.db.session import get_db
from app.schemas.source_dependency import (
    ArticleProvenanceCreate,
    ArticleProvenanceRead,
    ArticleProvenanceVerificationUpdate,
)
from app.services.source_dependency import SourceDependencyService


router = APIRouter(
    prefix="/articles",
    tags=["article-provenance"],
)

service = SourceDependencyService()


@router.get(
    "/{article_id}/provenance",
    response_model=list[ArticleProvenanceRead],
)
def list_article_provenance(
    article_id: UUID,
    db: Session = Depends(get_db),
):
    return service.list_article_provenance(
        db,
        article_id=article_id,
    )


@router.post(
    "/{article_id}/provenance",
    response_model=ArticleProvenanceRead,
    status_code=201,
)
def create_article_provenance(
    article_id: UUID,
    data: ArticleProvenanceCreate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_source_admin),
):
    provenance = service.create_article_provenance(
        db,
        article_id=article_id,
        data=data,
    )
    db.commit()
    db.refresh(provenance)
    return provenance


@router.patch(
    "/{article_id}/provenance/{provenance_id}",
    response_model=ArticleProvenanceRead,
)
def update_article_provenance_verification(
    article_id: UUID,
    provenance_id: UUID,
    data: ArticleProvenanceVerificationUpdate,
    db: Session = Depends(get_db),
    _admin: None = Depends(require_source_admin),
):
    provenance = service.update_article_provenance_verification(
        db,
        article_id=article_id,
        provenance_id=provenance_id,
        data=data,
    )
    db.commit()
    db.refresh(provenance)
    return provenance
