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
from app.repositories.source import SourceRepository
from app.schemas.source import SourceCreate


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