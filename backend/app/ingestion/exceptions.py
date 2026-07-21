class IngestionError(Exception):
    """Base exception for feed ingestion failures."""


class FeedFetchError(IngestionError):
    """Base exception for HTTP feed retrieval failures."""


class InvalidFeedUrlError(FeedFetchError):
    """Raised when a feed URL is empty, malformed, or unsupported."""


class FeedTimeoutError(FeedFetchError):
    """Raised when a feed request exceeds its timeout."""


class FeedConnectionError(FeedFetchError):
    """Raised when a feed cannot be reached."""


class FeedHttpStatusError(FeedFetchError):
    """Raised when a feed endpoint returns an unsuccessful status code."""

    def __init__(self, *, url: str, status_code: int) -> None:
        self.url = url
        self.status_code = status_code
        super().__init__(f"Feed request to {url!r} returned HTTP {status_code}.")


class FeedResponseTooLargeError(FeedFetchError):
    """Raised when a response exceeds the configured byte limit."""


class FeedParseError(IngestionError):
    """Base exception for feed parsing failures."""


class EmptyFeedError(FeedParseError):
    """Raised when no feed payload is available for parsing."""


class UnsupportedFeedFormatError(FeedParseError):
    """Raised when the payload is neither supported RSS nor Atom."""
