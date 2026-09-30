from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.agency_provenance import detect_agency_provenance
from app.core.article_identity import ArticleIdentity, build_article_identity
from app.enums.article_identity_type import ArticleIdentityType
from app.enums.confirmation_role import resolve_confirmation_role
from app.enums.source_dependency import ArticleProvenanceKind
from app.ingestion.models import FeedFetchResult, ParsedFeed, ParsedFeedEntry
from app.models.article import Article
from app.models.feed import Feed
from app.repositories.article import ArticleRepository
from app.repositories.source import SourceRepository
from app.repositories.source_dependency import SourceDependencyRepository


@dataclass(frozen=True, slots=True)
class FeedPersistenceResult:
    inserted: int
    updated: int
    unchanged: int


class FeedPersistenceService:
    def __init__(
        self,
        article_repository: ArticleRepository | None = None,
        source_repository: SourceRepository | None = None,
        source_dependency_repository: SourceDependencyRepository | None = None,
    ) -> None:
        self.article_repository = article_repository or ArticleRepository()
        self.source_repository = source_repository or SourceRepository()
        self.source_dependency_repository = (
            source_dependency_repository or SourceDependencyRepository()
        )

    def persist(
        self,
        db: Session,
        *,
        feed: Feed,
        parsed_feed: ParsedFeed,
        fetch_result: FeedFetchResult | None = None,
        fetched_at: datetime | None = None,
    ) -> FeedPersistenceResult:
        now = fetched_at or datetime.now(UTC)
        inserted = 0
        updated = 0
        unchanged = 0

        for entry in parsed_feed.entries:
            identity = build_article_identity(entry)
            article = self._find_existing(db, feed, entry, identity)

            if article is None:
                article, was_inserted = self._create_or_get(
                    db, feed, entry, identity
                )
                if was_inserted:
                    inserted += 1
                elif self._apply_entry(article, entry, identity):
                    updated += 1
                else:
                    unchanged += 1
            elif self._apply_entry(article, entry, identity):
                updated += 1
            else:
                unchanged += 1

            self._persist_detected_agency_provenance(
                db,
                feed=feed,
                article=article,
                entry=entry,
            )

        feed.last_fetched_at = now
        feed.last_success_at = now
        feed.last_error_at = None
        feed.last_error_message = None

        if fetch_result is not None:
            feed.etag = fetch_result.etag
            feed.last_modified = fetch_result.last_modified

        self.article_repository.flush(db)
        return FeedPersistenceResult(
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
        )

    def _persist_detected_agency_provenance(
        self,
        db: Session,
        *,
        feed: Feed,
        article: Article,
        entry: ParsedFeedEntry,
    ) -> None:
        candidate = detect_agency_provenance(
            author=entry.author,
            provider=entry.provider,
        )
        if candidate is None:
            return

        upstream_source = self.source_repository.get_by_slug(
            db,
            candidate.source_slug,
        )
        if upstream_source is None or not upstream_source.active:
            return
        if upstream_source.id == feed.source_id:
            return

        self.source_dependency_repository.add_pending_article_provenance_candidate(
            db,
            article_id=article.id,
            upstream_source_id=upstream_source.id,
            relation_kind=ArticleProvenanceKind.SUPPLIED_BY,
            confidence=candidate.confidence,
            detection_method=candidate.detection_method,
            notes=(
                "Automatically detected agency provenance candidate from "
                f"{candidate.detection_method.value}: {candidate.evidence}"
            ),
        )

    def _create_or_get(
        self,
        db: Session,
        feed: Feed,
        entry: ParsedFeedEntry,
        identity: ArticleIdentity,
    ) -> tuple[Article, bool]:
        values = {
            "feed_id": feed.id,
            "identity_type": identity.identity_type,
            "identity_key": identity.identity_key,
            "guid": self._clean(entry.external_id),
            "link": self._clean(entry.link),
            "title": self._clean(entry.title),
            "summary": entry.summary,
            "content": entry.content,
            "author": self._clean(entry.author),
            "published_at": entry.published_at,
            "source_updated_at": entry.updated_at,
            "confirmation_role": resolve_confirmation_role(
                source_type=feed.source.source_type,
                feed_default=feed.default_confirmation_role,
            ),
        }
        article_id = db.scalar(
            insert(Article)
            .values(**values)
            .on_conflict_do_nothing(
                constraint="uq_articles_feed_id_identity_key"
            )
            .returning(Article.id)
        )
        if article_id is not None:
            article = db.get(Article, article_id)
            assert article is not None
            return article, True

        article = db.scalar(
            select(Article).where(
                Article.feed_id == feed.id,
                Article.identity_key == identity.identity_key,
                Article.deleted_at.is_(None),
            )
        )
        if article is None:
            raise RuntimeError("conflicting article could not be reloaded")
        return article, False

    def _find_existing(
        self,
        db: Session,
        feed: Feed,
        entry: ParsedFeedEntry,
        identity: ArticleIdentity,
    ) -> Article | None:
        guid = self._clean(entry.external_id)
        if guid:
            article = self.article_repository.get_by_guid(
                db,
                feed_id=feed.id,
                guid=guid,
            )
            if article is not None:
                return article

        link = self._clean(entry.link)
        if link:
            article = self.article_repository.get_by_link(
                db,
                feed_id=feed.id,
                link=link,
            )
            if article is not None:
                if (
                    guid
                    and article.identity_type
                    is ArticleIdentityType.GUID
                ):
                    return None
                return article

        article = self.article_repository.get_by_identity(
            db,
            feed_id=feed.id,
            identity_key=identity.identity_key,
        )

        if article is not None:
            return article

        if identity.identity_type is not ArticleIdentityType.DERIVED:
            derived_entry = ParsedFeedEntry(
                external_id=None,
                title=entry.title,
                link=None,
                summary=entry.summary,
                content=entry.content,
                author=entry.author,
                published_at=entry.published_at,
                updated_at=entry.updated_at,
                categories=entry.categories,
                enclosures=entry.enclosures,
            )
            derived_identity = build_article_identity(
                derived_entry
            )

            return self.article_repository.get_by_identity(
                db,
                feed_id=feed.id,
                identity_key=(
                    derived_identity.identity_key
                ),
            )

        return None

    @staticmethod
    def _apply_entry(
        article: Article,
        entry: ParsedFeedEntry,
        identity: ArticleIdentity,
    ) -> bool:
        values = {
            "guid": FeedPersistenceService._clean(entry.external_id),
            "link": FeedPersistenceService._clean(entry.link),
            "title": FeedPersistenceService._clean(entry.title),
            "summary": entry.summary,
            "content": entry.content,
            "author": FeedPersistenceService._clean(entry.author),
            "published_at": entry.published_at,
            "source_updated_at": entry.updated_at,
        }

        changed = False
        normalization_input_changed = False
        for field, value in values.items():
            if getattr(article, field) != value:
                setattr(article, field, value)
                changed = True
                if field in {"title", "summary", "content"}:
                    normalization_input_changed = True

        if normalization_input_changed:
            article.normalized_title = None
            article.normalized_text = None
            article.language_code = None
            article.word_count = None
            article.reading_time_minutes = None
            article.content_hash = None
            article.normalization_version = None
            article.normalized_at = None

        should_upgrade_identity = (
            (
                identity.identity_type
                is ArticleIdentityType.GUID
                and article.identity_type
                is not ArticleIdentityType.GUID
            )
            or (
                identity.identity_type
                is ArticleIdentityType.LINK
                and article.identity_type
                is ArticleIdentityType.DERIVED
            )
        )

        if should_upgrade_identity:
            article.identity_type = identity.identity_type
            article.identity_key = identity.identity_key
            changed = True

        return changed

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
