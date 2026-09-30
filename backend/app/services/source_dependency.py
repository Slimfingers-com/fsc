from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationError
from app.enums.source_dependency import (
    ArticleProvenanceDetectionMethod,
    ArticleProvenanceKind,
)
from app.models.source_dependency import ArticleProvenance
from app.repositories.source import SourceRepository
from app.repositories.source_dependency import SourceDependencyRepository
from app.schemas.source_dependency import (
    ArticleProvenanceCreate,
    ArticleProvenanceReviewItem,
    ArticleProvenanceReviewPage,
    ArticleProvenanceVerificationUpdate,
)


class SourceDependencyService:
    def __init__(
        self,
        repository: SourceDependencyRepository | None = None,
        source_repository: SourceRepository | None = None,
    ) -> None:
        self.repository = repository or SourceDependencyRepository()
        self.source_repository = source_repository or SourceRepository()

    def list_article_provenance(
        self,
        db: Session,
        *,
        article_id: UUID,
    ) -> list[ArticleProvenance]:
        source_id = self.repository.get_active_article_source_id(
            db,
            article_id=article_id,
        )
        if source_id is None:
            raise BusinessRuleViolationError(
                "Der Artikel existiert nicht oder ist nicht verfügbar."
            )
        return self.repository.list_article_provenance(
            db,
            article_id=article_id,
        )

    def list_article_provenance_review_queue(
        self,
        db: Session,
        *,
        verified: bool,
        upstream_source_id: UUID | None,
        publisher_source_id: UUID | None,
        detection_method: ArticleProvenanceDetectionMethod | None,
        relation_kind: ArticleProvenanceKind | None,
        min_confidence: float | None,
        created_from: datetime | None,
        limit: int,
        offset: int,
    ) -> ArticleProvenanceReviewPage:
        total, rows = self.repository.list_article_provenance_review_queue(
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
        items = [
            ArticleProvenanceReviewItem(
                provenance_id=provenance.id,
                article_id=article.id,
                article_title=article.title,
                article_url=article.link,
                article_author=article.author,
                article_published_at=article.published_at,
                publisher_source_id=publisher.id,
                publisher_source_name=publisher.name,
                publisher_source_slug=publisher.slug,
                upstream_source_id=upstream.id,
                upstream_source_name=upstream.name,
                upstream_source_slug=upstream.slug,
                relation_kind=provenance.relation_kind,
                confidence=provenance.confidence,
                detection_method=provenance.detection_method,
                verified=provenance.verified,
                notes=provenance.notes,
                created_at=provenance.created_at,
            )
            for provenance, article, publisher, upstream in rows
        ]
        return ArticleProvenanceReviewPage(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
        )

    def create_article_provenance(
        self,
        db: Session,
        *,
        article_id: UUID,
        data: ArticleProvenanceCreate,
    ) -> ArticleProvenance:
        article_source_id = self.repository.get_active_article_source_id(
            db,
            article_id=article_id,
        )
        if article_source_id is None:
            raise BusinessRuleViolationError(
                "Der Artikel existiert nicht oder ist nicht verfügbar."
            )

        upstream_source = self.source_repository.get_active_by_id(
            db,
            data.upstream_source_id,
        )
        if upstream_source is None:
            raise BusinessRuleViolationError(
                "Die Upstream-Quelle existiert nicht oder ist nicht aktiv."
            )

        if data.upstream_article_id is not None:
            upstream_article_source_id = (
                self.repository.get_active_article_source_id(
                    db,
                    article_id=data.upstream_article_id,
                )
            )
            if upstream_article_source_id is None:
                raise BusinessRuleViolationError(
                    "Der Upstream-Artikel existiert nicht oder ist nicht verfügbar."
                )
            if upstream_article_source_id != data.upstream_source_id:
                raise BusinessRuleViolationError(
                    "Der Upstream-Artikel gehört nicht zur angegebenen Upstream-Quelle."
                )

        provenance = ArticleProvenance(
            article_id=article_id,
            upstream_source_id=data.upstream_source_id,
            upstream_article_id=data.upstream_article_id,
            relation_kind=data.relation_kind,
            confidence=data.confidence,
            detection_method=data.detection_method,
            verified=data.verified,
            provenance_url=(
                str(data.provenance_url)
                if data.provenance_url is not None
                else None
            ),
            notes=data.notes,
        )

        try:
            self.repository.add_article_provenance(
                db,
                provenance,
            )
            db.flush()
        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            )
            if constraint_name == "uq_article_provenance_active_identity":
                raise BusinessRuleViolationError(
                    "Diese Artikel-Provenienz existiert bereits."
                ) from exc
            if constraint_name == "ck_article_provenance_distinct_articles":
                raise BusinessRuleViolationError(
                    "Ein Artikel kann nicht sein eigener Upstream-Artikel sein."
                ) from exc
            raise

        return provenance

    def update_article_provenance_verification(
        self,
        db: Session,
        *,
        article_id: UUID,
        provenance_id: UUID,
        data: ArticleProvenanceVerificationUpdate,
    ) -> ArticleProvenance:
        article_source_id = self.repository.get_active_article_source_id(
            db,
            article_id=article_id,
        )
        if article_source_id is None:
            raise BusinessRuleViolationError(
                "Der Artikel existiert nicht oder ist nicht verfügbar."
            )

        provenance = self.repository.get_active_article_provenance(
            db,
            article_id=article_id,
            provenance_id=provenance_id,
        )
        if provenance is None:
            raise BusinessRuleViolationError(
                "Die Artikel-Provenienz existiert nicht oder gehört nicht "
                "zu diesem Artikel."
            )

        if provenance.verified != data.verified:
            provenance.verified = data.verified
            db.flush()

        return provenance
