from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.enums.source_dependency import (
    ArticleProvenanceDetectionMethod,
    ArticleProvenanceKind,
    ArticleProvenanceReviewStatus,
    SourceRelationKind,
)


class SourceRelationCreate(BaseModel):
    related_source_id: UUID
    relation_kind: SourceRelationKind
    valid_from: date | None = None
    valid_to: date | None = None
    provenance_url: HttpUrl | None = None
    reference_date: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_validity_range(self):
        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_to < self.valid_from
        ):
            raise ValueError("valid_to must not be before valid_from")
        return self


class SourceRelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    related_source_id: UUID
    relation_kind: SourceRelationKind
    valid_from: date | None
    valid_to: date | None
    provenance_url: str | None
    reference_date: date | None
    notes: str | None


class ArticleProvenanceCreate(BaseModel):
    upstream_source_id: UUID
    upstream_article_id: UUID | None = None
    relation_kind: ArticleProvenanceKind
    confidence: float = Field(default=1.0, ge=0, le=1)
    detection_method: ArticleProvenanceDetectionMethod = (
        ArticleProvenanceDetectionMethod.MANUAL
    )
    review_status: ArticleProvenanceReviewStatus = (
        ArticleProvenanceReviewStatus.PENDING
    )
    provenance_url: HttpUrl | None = None
    notes: str | None = None


class ArticleProvenanceReviewUpdate(BaseModel):
    review_status: ArticleProvenanceReviewStatus


class ArticleProvenanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    article_id: UUID
    upstream_source_id: UUID
    upstream_article_id: UUID | None
    relation_kind: ArticleProvenanceKind
    confidence: float
    detection_method: ArticleProvenanceDetectionMethod
    review_status: ArticleProvenanceReviewStatus
    reviewed_at: datetime | None
    provenance_url: str | None
    notes: str | None


class ArticleProvenanceReviewItem(BaseModel):
    provenance_id: UUID
    article_id: UUID
    article_title: str | None
    article_url: str | None
    article_author: str | None
    article_published_at: datetime | None
    publisher_source_id: UUID
    publisher_source_name: str
    publisher_source_slug: str
    upstream_source_id: UUID
    upstream_source_name: str
    upstream_source_slug: str
    relation_kind: ArticleProvenanceKind
    confidence: float
    detection_method: ArticleProvenanceDetectionMethod
    review_status: ArticleProvenanceReviewStatus
    reviewed_at: datetime | None
    notes: str | None
    created_at: datetime


class ArticleProvenanceReviewPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ArticleProvenanceReviewItem]
