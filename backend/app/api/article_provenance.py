from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.sources import require_source_admin
from app.db.session import get_db
from app.enums.source_dependency import (
    ArticleProvenanceDetectionMethod,
    ArticleProvenanceKind,
)
from app.schemas.source_dependency import (
    ArticleProvenanceCreate,
    ArticleProvenanceRead,
    ArticleProvenanceReviewPage,
    ArticleProvenanceVerificationUpdate,
)
from app.services.source_dependency import SourceDependencyService


router = APIRouter(
    prefix="/articles",
    tags=["article-provenance"],
)

review_router = APIRouter(
    prefix="/article-provenance",
    tags=["article-provenance"],
)

service = SourceDependencyService()


@review_router.get(
    "/review-queue",
    response_model=ArticleProvenanceReviewPage,
)
def list_article_provenance_review_queue(
    verified: bool = False,
    upstream_source_id: UUID | None = None,
    publisher_source_id: UUID | None = None,
    detection_method: ArticleProvenanceDetectionMethod | None = None,
    relation_kind: ArticleProvenanceKind | None = None,
    min_confidence: float | None = Query(default=None, ge=0, le=1),
    created_from: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin: None = Depends(require_source_admin),
):
    return service.list_article_provenance_review_queue(
        db,
        verified=verified,
        upstream_source_id=upstream_source_id,
        publisher_source_id=publisher_source_id,
        detection_method=detection_method,
        relation_kind=relation_kind,
        min_confidence=min_confidence,
        created_from=created_from,
        limit=limit,
        offset=offset,
    )


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
