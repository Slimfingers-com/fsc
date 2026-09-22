from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleViolationError,
    DuplicateSourceError,
)
from app.core.slug import generate_slug
from app.core.source_identity import normalize_source_name
from app.models.feed import Feed
from app.models.source import Source
from app.models.source_metadata import (
    SourceClassification,
    SourceMetric,
    SourceOutlet,
)
from app.repositories.source import SourceRepository
from app.schemas.source import SourceCreate
from app.schemas.source_metadata import (
    SourceClassificationCreate,
    SourceMetricCreate,
    SourceOutletCreate,
)


class SourceService:
    def __init__(
        self,
        repository: SourceRepository | None = None,
    ) -> None:
        self.repository = repository or SourceRepository()

    def get_by_slug(
        self,
        db: Session,
        slug: str,
    ) -> Source | None:
        return self.repository.get_by_slug(db, slug)

    def list_active(
        self,
        db: Session,
    ) -> list[Source]:
        return self.repository.list_active(db)

    def create_source(
        self,
        db: Session,
        data: SourceCreate,
    ) -> Source:
        normalized_name = normalize_source_name(data.name)

        if self.repository.exists_by_normalized_name(
            db,
            normalized_name,
        ):
            raise DuplicateSourceError(
                f'Die Quelle "{data.name}" existiert bereits.'
            )

        base_slug = generate_slug(data.name)

        if not base_slug:
            raise BusinessRuleViolationError(
                "Aus dem Quellennamen konnte kein gültiger Slug erzeugt werden."
            )

        self._validate_feeds(data)
        self._validate_outlets(data)

        slug = base_slug
        suffix = 2

        while self.repository.exists_by_slug(db, slug):
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        source = Source(
            name=data.name.strip(),
            normalized_name=normalized_name,
            slug=slug,
            description=data.description,
            url=str(data.url),
            api_url=str(data.api_url) if data.api_url else None,
            source_type=data.source_type,
            coverage_scope=data.coverage_scope,
            country=data.country,
            language=data.language,
            ownership=data.ownership,
            funding_model=data.funding_model,
            paywall=data.paywall,
            transparency_level=data.transparency_level,
            correction_policy=data.correction_policy,
            primary_source_usage=data.primary_source_usage,
            priority_tier=data.priority_tier,
            feeds=[
                Feed(
                    name=feed.name.strip(),
                    url=str(feed.url),
                    active=feed.active,
                    priority=feed.priority,
                    fetch_interval_minutes=feed.fetch_interval_minutes,
                )
                for feed in data.feeds
            ],
            outlets=[
                SourceOutlet(
                    name=outlet.name.strip(),
                    normalized_name=normalize_source_name(outlet.name),
                    media_category=outlet.media_category,
                    publication_form=outlet.publication_form,
                    publication_frequency=outlet.publication_frequency,
                    language=outlet.language,
                    url=str(outlet.url) if outlet.url else None,
                    is_primary=outlet.is_primary,
                    active=outlet.active,
                )
                for outlet in data.outlets
            ],
        )

        try:
            self.repository.add(db, source)
            self.repository.flush(db)
        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            )

            if constraint_name in {
                "ix_sources_normalized_name",
                "ix_sources_slug",
            }:
                raise DuplicateSourceError(
                    f'Die Quelle "{data.name}" existiert bereits.'
                ) from exc

            if constraint_name == "uq_feeds_url":
                raise BusinessRuleViolationError(
                    "Mindestens eine Feed-URL ist bereits einer anderen Quelle "
                    "zugeordnet."
                ) from exc

            if constraint_name == "uq_feeds_source_id_name":
                raise BusinessRuleViolationError(
                    "Feed-Namen müssen innerhalb einer Quelle eindeutig sein."
                ) from exc

            if constraint_name == "uq_source_outlet_source_normalized_name":
                raise BusinessRuleViolationError(
                    "Outlet-Namen müssen innerhalb einer Quelle eindeutig sein."
                ) from exc

            raise

        return source

    def create_outlet(
        self,
        db: Session,
        source: Source,
        data: SourceOutletCreate,
    ) -> SourceOutlet:
        outlet = SourceOutlet(
            source_id=source.id,
            name=data.name.strip(),
            normalized_name=normalize_source_name(data.name),
            media_category=data.media_category,
            publication_form=data.publication_form,
            publication_frequency=data.publication_frequency,
            language=data.language,
            url=str(data.url) if data.url else None,
            is_primary=data.is_primary,
            active=data.active,
        )

        try:
            self.repository.add_outlet(db, outlet)
            self.repository.flush(db)
        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            )
            if constraint_name == "uq_source_outlet_source_normalized_name":
                raise BusinessRuleViolationError(
                    "Dieses Outlet existiert für die Quelle bereits."
                ) from exc
            if constraint_name == "ck_source_outlet_name_nonempty":
                raise BusinessRuleViolationError(
                    "Ein Outlet-Name darf nicht leer sein."
                ) from exc
            raise

        return outlet

    def create_classification(
        self,
        db: Session,
        source: Source,
        data: SourceClassificationCreate,
    ) -> SourceClassification:
        classification = SourceClassification(
            source_id=source.id,
            dimension=data.dimension,
            value=data.value.strip(),
            detail=data.detail,
            classifier_type=data.classifier_type,
            classifier_name=data.classifier_name.strip(),
            source_url=str(data.source_url),
            reference_date=data.reference_date,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
            retrieved_at=data.retrieved_at,
            notes=data.notes,
        )

        try:
            self.repository.add_classification(db, classification)
            self.repository.flush(db)
        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            )
            if constraint_name == "uq_source_classification_assertion":
                raise BusinessRuleViolationError(
                    "Diese Quellenklassifikation existiert bereits."
                ) from exc
            if constraint_name in {
                "ck_source_classification_value_nonempty",
                "ck_source_classification_classifier_nonempty",
            }:
                raise BusinessRuleViolationError(
                    "Klassifikationswert und Klassifizierer dürfen nicht leer sein."
                ) from exc
            raise

        return classification

    def create_metric(
        self,
        db: Session,
        source: Source,
        data: SourceMetricCreate,
    ) -> SourceMetric:
        if data.outlet_id is not None:
            outlet = self.repository.get_active_outlet(
                db,
                data.outlet_id,
            )
            if outlet is None or outlet.source_id != source.id:
                raise BusinessRuleViolationError(
                    "Das angegebene Outlet gehört nicht zu dieser Quelle."
                )

        metric = SourceMetric(
            source_id=source.id,
            outlet_id=data.outlet_id,
            metric_kind=data.metric_kind,
            value=data.value,
            unit=data.unit.strip(),
            metric_scope=data.metric_scope.strip(),
            reference_period=data.reference_period.strip(),
            period_start=data.period_start,
            period_end=data.period_end,
            measurement_body=data.measurement_body.strip(),
            source_url=str(data.source_url),
            audited=data.audited,
            retrieved_at=data.retrieved_at,
            notes=data.notes,
        )

        try:
            self.repository.add_metric(db, metric)
            self.repository.flush(db)
        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None,
            )
            if constraint_name == "uq_source_metric_measurement":
                raise BusinessRuleViolationError(
                    "Dieser Reichweitenmesswert existiert bereits."
                ) from exc
            if constraint_name in {
                "ck_source_metric_scope_nonempty",
                "ck_source_metric_unit_nonempty",
                "ck_source_metric_reference_period_nonempty",
                "ck_source_metric_measurement_body_nonempty",
            }:
                raise BusinessRuleViolationError(
                    "Messwert-Metadaten dürfen nicht leer sein."
                ) from exc
            raise

        return metric

    @staticmethod
    def _validate_feeds(
        data: SourceCreate,
    ) -> None:
        feed_names: set[str] = set()
        feed_urls: set[str] = set()

        for feed in data.feeds:
            feed_name = feed.name.strip()
            feed_url = str(feed.url)

            if not feed_name:
                raise BusinessRuleViolationError(
                    "Ein Feed-Name darf nicht nur aus Leerzeichen bestehen."
                )

            normalized_feed_name = feed_name.casefold()

            if normalized_feed_name in feed_names:
                raise BusinessRuleViolationError(
                    "Feed-Namen müssen innerhalb einer Quelle eindeutig sein."
                )

            if feed_url in feed_urls:
                raise BusinessRuleViolationError(
                    "Eine Feed-URL darf innerhalb einer Quelle nur einmal "
                    "verwendet werden."
                )

            feed_names.add(normalized_feed_name)
            feed_urls.add(feed_url)

    @staticmethod
    def _validate_outlets(
        data: SourceCreate,
    ) -> None:
        names: set[str] = set()

        for outlet in data.outlets:
            name = outlet.name.strip()
            if not name:
                raise BusinessRuleViolationError(
                    "Ein Outlet-Name darf nicht nur aus Leerzeichen bestehen."
                )

            normalized = normalize_source_name(name)
            if normalized in names:
                raise BusinessRuleViolationError(
                    "Outlet-Namen müssen innerhalb einer Quelle eindeutig sein."
                )
            names.add(normalized)
