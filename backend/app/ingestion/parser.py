from collections.abc import Mapping, Sequence
from typing import Any

import feedparser

from app.ingestion.datetime_utils import normalize_feed_datetime
from app.ingestion.exceptions import EmptyFeedError, UnsupportedFeedFormatError
from app.ingestion.models import (
    FeedFetchResult,
    FeedFormat,
    ParsedFeed,
    ParsedFeedEnclosure,
    ParsedFeedEntry,
)


class FeedParser:
    """Normalize RSS 2.x and Atom feeds into stable ingestion DTOs."""

    def parse(self, fetch_result: FeedFetchResult) -> ParsedFeed:
        if fetch_result.not_modified:
            raise EmptyFeedError("HTTP 304 contains no feed document to parse.")
        if not fetch_result.content:
            raise EmptyFeedError("Feed response contains no content.")

        response_headers: dict[str, str] = {}
        if fetch_result.content_type:
            response_headers["content-type"] = fetch_result.content_type

        document = feedparser.parse(
            fetch_result.content,
            response_headers=response_headers,
        )
        feed_format = self._detect_format(document)
        feed = document.get("feed") or {}

        return ParsedFeed(
            source_url=fetch_result.final_url,
            format=feed_format,
            version=str(document.get("version") or ""),
            title=self._text(feed.get("title")),
            link=self._feed_link(feed),
            description=self._first_text(
                feed.get("subtitle"),
                feed.get("description"),
                feed.get("summary"),
            ),
            language=self._text(feed.get("language")),
            updated_at=normalize_feed_datetime(
                feed.get("updated_parsed") or feed.get("published_parsed")
            ),
            entries=tuple(
                self._parse_entry(entry)
                for entry in document.get("entries", ())
            ),
            warnings=self._warnings(document),
        )

    @staticmethod
    def _detect_format(document: Mapping[str, Any]) -> FeedFormat:
        version = str(document.get("version") or "").lower()
        if version.startswith("rss"):
            return FeedFormat.RSS
        if version.startswith("atom"):
            return FeedFormat.ATOM
        raise UnsupportedFeedFormatError(
            "Document is neither supported RSS nor Atom."
        )

    def _parse_entry(self, entry: Mapping[str, Any]) -> ParsedFeedEntry:
        return ParsedFeedEntry(
            external_id=self._first_text(entry.get("id"), entry.get("guid")),
            title=self._text(entry.get("title")),
            link=self._entry_link(entry),
            summary=self._first_text(
                entry.get("summary"), entry.get("description")
            ),
            content=self._entry_content(entry),
            author=self._entry_author(entry),
            published_at=normalize_feed_datetime(
                entry.get("published_parsed") or entry.get("created_parsed")
            ),
            updated_at=normalize_feed_datetime(
                entry.get("updated_parsed") or entry.get("modified_parsed")
            ),
            categories=self._categories(entry),
            enclosures=self._enclosures(entry),
        )

    def _feed_link(self, feed: Mapping[str, Any]) -> str | None:
        direct = self._text(feed.get("link"))
        if direct:
            return direct
        return self._alternate_link(feed.get("links"))

    def _entry_link(self, entry: Mapping[str, Any]) -> str | None:
        direct = self._text(entry.get("link"))
        if direct:
            return direct
        return self._alternate_link(entry.get("links"))

    def _alternate_link(self, links: Any) -> str | None:
        if not isinstance(links, Sequence) or isinstance(links, (str, bytes)):
            return None
        fallback: str | None = None
        for link in links:
            if not isinstance(link, Mapping):
                continue
            href = self._text(link.get("href"))
            if not href:
                continue
            fallback = fallback or href
            if self._text(link.get("rel")) in {None, "alternate"}:
                return href
        return fallback

    def _entry_content(self, entry: Mapping[str, Any]) -> str | None:
        contents = entry.get("content") or ()
        if isinstance(contents, Sequence) and not isinstance(contents, (str, bytes)):
            for content in contents:
                if isinstance(content, Mapping):
                    value = self._text(content.get("value"))
                    if value:
                        return value
        return None

    def _entry_author(self, entry: Mapping[str, Any]) -> str | None:
        detail = entry.get("author_detail")
        if isinstance(detail, Mapping):
            name = self._text(detail.get("name"))
            if name:
                return name
        return self._text(entry.get("author"))

    def _categories(self, entry: Mapping[str, Any]) -> tuple[str, ...]:
        values: list[str] = []
        tags = entry.get("tags") or ()
        if isinstance(tags, Sequence) and not isinstance(tags, (str, bytes)):
            for tag in tags:
                if not isinstance(tag, Mapping):
                    continue
                term = self._text(tag.get("term"))
                if term and term not in values:
                    values.append(term)
        return tuple(values)

    def _enclosures(
        self, entry: Mapping[str, Any]
    ) -> tuple[ParsedFeedEnclosure, ...]:
        result: list[ParsedFeedEnclosure] = []
        enclosures = entry.get("enclosures") or ()
        if not isinstance(enclosures, Sequence) or isinstance(enclosures, (str, bytes)):
            return ()
        for enclosure in enclosures:
            if not isinstance(enclosure, Mapping):
                continue
            url = self._first_text(enclosure.get("href"), enclosure.get("url"))
            if not url:
                continue
            result.append(
                ParsedFeedEnclosure(
                    url=url,
                    content_type=self._text(enclosure.get("type")),
                    length_bytes=self._non_negative_int(enclosure.get("length")),
                )
            )
        return tuple(result)

    @staticmethod
    def _warnings(document: Mapping[str, Any]) -> tuple[str, ...]:
        if not document.get("bozo"):
            return ()
        exception = document.get("bozo_exception")
        return (str(exception) if exception else "Malformed feed document.",)

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _first_text(self, *values: Any) -> str | None:
        for value in values:
            text = self._text(value)
            if text:
                return text
        return None

    @staticmethod
    def _non_negative_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number >= 0 else None
