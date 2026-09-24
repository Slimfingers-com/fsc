from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolationError
from app.models.source_dependency import ArticleProvenance
from app.repositories.source import SourceRepository
from app.repositories.source_dependency import SourceDependencyRepository
from app.schemas.source_dependency import ArticleProvenanceCreate


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
