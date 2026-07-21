from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.article_identity import ArticleIdentity, build_article_identity
from app.enums.article_identity_type import ArticleIdentityType
from app.ingestion.models import FeedFetchResult, ParsedFeed, ParsedFeedEntry
from app.models.article import Article
from app.models.feed import Feed
from app.repositories.article import ArticleRepository


@dataclass(frozen=True, slots=True)
class FeedPersistenceResult:
    inserted: int
    updated: int
    unchanged: int


class FeedPersistenceService:
    def __init__(
        self,
        article_repository: ArticleRepository | None = None,
    ) -> None:
        self.article_repository = article_repository or ArticleRepository()

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
                self.article_repository.add(
                    db,
                    self._new_article(feed, entry, identity),
                )
                inserted += 1
            elif self._apply_entry(article, entry, identity):
                updated += 1
            else:
                unchanged += 1

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
                return article

        return self.article_repository.get_by_identity(
            db,
            feed_id=feed.id,
            identity_key=identity.identity_key,
        )

    @staticmethod
    def _new_article(
        feed: Feed,
        entry: ParsedFeedEntry,
        identity: ArticleIdentity,
    ) -> Article:
        return Article(
            feed=feed,
            identity_type=identity.identity_type,
            identity_key=identity.identity_key,
            guid=FeedPersistenceService._clean(entry.external_id),
            link=FeedPersistenceService._clean(entry.link),
            title=FeedPersistenceService._clean(entry.title),
            summary=entry.summary,
            content=entry.content,
            author=FeedPersistenceService._clean(entry.author),
            published_at=entry.published_at,
            source_updated_at=entry.updated_at,
        )

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

        if (
            identity.identity_type is ArticleIdentityType.GUID
            and article.identity_type is not ArticleIdentityType.GUID
        ):
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
