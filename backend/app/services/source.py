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
from app.models.source_metadata import SourceClassification, SourceReachMetric
from app.repositories.source import SourceRepository
from app.schemas.source import (
    SourceClassificationCreate,
    SourceCreate,
    SourceReachMetricCreate,
    SourceUpdate,
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
            content_languages=list(data.content_languages),
            media_family=data.media_family,
            publication_format=data.publication_format,
            publication_frequency=data.publication_frequency,
            coverage_countries=list(data.coverage_countries),
            ownership=data.ownership,
            funding_model=data.funding_model,
            paywall=data.paywall,
            transparency_level=data.transparency_level,
            correction_policy=data.correction_policy,
            primary_source_usage=data.primary_source_usage,
            priority_tier=data.priority_tier,
            classifications=[
                SourceClassification(
                    kind=item.kind,
                    value=item.value,
                    detail=item.detail,
                    evidence_source_name=item.evidence_source_name.strip(),
                    evidence_url=str(item.evidence_url) if item.evidence_url else None,
                    as_of=item.as_of,
                    is_primary=item.is_primary,
                    notes=item.notes,
                )
                for item in data.classifications
            ],
            reach_metrics=[
                SourceReachMetric(
                    metric_type=item.metric_type,
                    metric_value=item.metric_value,
                    period_start=item.period_start,
                    period_end=item.period_end,
                    evidence_source_name=item.evidence_source_name.strip(),
                    evidence_url=str(item.evidence_url) if item.evidence_url else None,
                    quality=item.quality,
                    notes=item.notes,
                )
                for item in data.reach_metrics
            ],
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

            raise

        return source

    def update_source(
        self,
        db: Session,
        *,
        slug: str,
        data: SourceUpdate,
    ) -> Source | None:
        source = self.get_by_slug(db, slug)
        if source is None:
            return None

        fields = data.model_fields_set
        simple_fields = (
            "description",
            "source_type",
            "coverage_scope",
            "country",
            "media_family",
            "publication_format",
            "publication_frequency",
            "ownership",
            "funding_model",
            "paywall",
            "active",
            "transparency_level",
            "correction_policy",
            "primary_source_usage",
            "priority_tier",
        )
        for field in simple_fields:
            if field in fields:
                setattr(source, field, getattr(data, field))

        if "language" in fields:
            source.language = data.language

        if "content_languages" in fields:
            source.content_languages = list(data.content_languages or [])
        elif "language" in fields and data.language is not None:
            languages = list(source.content_languages)
            if data.language not in languages:
                languages.insert(0, data.language)
            source.content_languages = languages

        if "coverage_countries" in fields:
            source.coverage_countries = list(data.coverage_countries or [])

        self.repository.flush(db)
        return source

    def add_classification(
        self,
        db: Session,
        *,
        slug: str,
        data: SourceClassificationCreate,
    ) -> Source | None:
        source = self.get_by_slug(db, slug)
        if source is None:
            return None

        if data.is_primary:
            changed = False
            for existing in source.classifications:
                if existing.kind == data.kind and existing.is_primary:
                    existing.is_primary = False
                    changed = True
            if changed:
                self.repository.flush(db)

        source.classifications.append(
            SourceClassification(
                kind=data.kind,
                value=data.value,
                detail=data.detail,
                evidence_source_name=data.evidence_source_name.strip(),
                evidence_url=str(data.evidence_url) if data.evidence_url else None,
                as_of=data.as_of,
                is_primary=data.is_primary,
                notes=data.notes,
            )
        )
        self.repository.flush(db)
        return source

    def add_reach_metric(
        self,
        db: Session,
        *,
        slug: str,
        data: SourceReachMetricCreate,
    ) -> Source | None:
        source = self.get_by_slug(db, slug)
        if source is None:
            return None

        source.reach_metrics.append(
            SourceReachMetric(
                metric_type=data.metric_type,
                metric_value=data.metric_value,
                period_start=data.period_start,
                period_end=data.period_end,
                evidence_source_name=data.evidence_source_name.strip(),
                evidence_url=str(data.evidence_url) if data.evidence_url else None,
                quality=data.quality,
                notes=data.notes,
            )
        )
        self.repository.flush(db)
        return source

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