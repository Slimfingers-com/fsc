from types import TracebackType
from urllib.parse import urlsplit

import httpx

from app.ingestion.exceptions import (
    FeedConnectionError,
    FeedHttpStatusError,
    FeedResponseTooLargeError,
    FeedTimeoutError,
    InvalidFeedUrlError,
)
from app.ingestion.models import FeedFetchRequest, FeedFetchResult


class FeedFetcher:
    """Synchronous HTTP client for RSS and Atom feeds."""

    DEFAULT_TIMEOUT_SECONDS = 15.0
    DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024
    DEFAULT_USER_AGENT = "FSC-Feed-Ingestion/0.1"

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be greater than zero")
        if not user_agent.strip():
            raise ValueError("user_agent must not be empty")

        self._client = client or httpx.Client()
        self._owns_client = client is None
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_response_bytes = max_response_bytes
        self._user_agent = user_agent

    def fetch(self, request: FeedFetchRequest) -> FeedFetchResult:
        url = request.url.strip()
        self._validate_url(url)

        headers = {
            "Accept": (
                "application/atom+xml, application/rss+xml, "
                "application/xml;q=0.9, text/xml;q=0.9, */*;q=0.1"
            ),
            "User-Agent": self._user_agent,
        }
        if request.etag:
            headers["If-None-Match"] = request.etag
        if request.last_modified:
            headers["If-Modified-Since"] = request.last_modified

        try:
            with self._client.stream(
                "GET",
                url,
                headers=headers,
                timeout=self._timeout,
                follow_redirects=True,
            ) as response:
                if response.status_code == 304:
                    return self._result(
                        request=request,
                        response=response,
                        content=None,
                    )

                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise FeedHttpStatusError(
                        url=str(response.url),
                        status_code=response.status_code,
                    ) from exc

                content = self._read_limited(response)
                return self._result(
                    request=request,
                    response=response,
                    content=content,
                )
        except FeedHttpStatusError:
            raise
        except FeedResponseTooLargeError:
            raise
        except httpx.TimeoutException as exc:
            raise FeedTimeoutError(f"Feed request to {url!r} timed out.") from exc
        except (httpx.InvalidURL, httpx.UnsupportedProtocol) as exc:
            raise InvalidFeedUrlError(f"Invalid feed URL: {url!r}.") from exc
        except httpx.RequestError as exc:
            raise FeedConnectionError(
                f"Feed request to {url!r} failed: {exc}."
            ) from exc

    def _read_limited(self, response: httpx.Response) -> bytes:
        declared_length = response.headers.get("content-length")
        if declared_length:
            try:
                if int(declared_length) > self._max_response_bytes:
                    raise FeedResponseTooLargeError(
                        "Feed response exceeds configured byte limit."
                    )
            except ValueError:
                pass

        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > self._max_response_bytes:
                raise FeedResponseTooLargeError(
                    "Feed response exceeds configured byte limit."
                )
        return bytes(body)

    @staticmethod
    def _result(
        *,
        request: FeedFetchRequest,
        response: httpx.Response,
        content: bytes | None,
    ) -> FeedFetchResult:
        return FeedFetchResult(
            requested_url=request.url.strip(),
            final_url=str(response.url),
            status_code=response.status_code,
            content=content,
            content_type=response.headers.get("content-type"),
            etag=response.headers.get("etag") or request.etag,
            last_modified=(
                response.headers.get("last-modified") or request.last_modified
            ),
        )

    @staticmethod
    def _validate_url(url: str) -> None:
        if not url:
            raise InvalidFeedUrlError("Feed URL must not be empty.")
        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            raise InvalidFeedUrlError(f"Invalid feed URL: {url!r}.") from exc
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise InvalidFeedUrlError(f"Invalid feed URL: {url!r}.")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "FeedFetcher":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
