from types import TracebackType
from urllib.parse import urljoin

import httpx

from app.ingestion.exceptions import (
    FeedConnectionError,
    FeedHttpStatusError,
    FeedResponseTooLargeError,
    FeedTimeoutError,
    InvalidFeedUrlError,
)
from app.ingestion.models import (
    FeedFetchRequest,
    FeedFetchResult,
)
from app.ingestion.url_policy import (
    FeedUrlPolicy,
    HostResolver,
)


class FeedFetcher:
    """Synchronous HTTP client for RSS and Atom feeds."""

    DEFAULT_TIMEOUT_SECONDS = 15.0
    DEFAULT_MAX_RESPONSE_BYTES = (
        10 * 1024 * 1024
    )
    DEFAULT_USER_AGENT = (
        "FSC-Feed-Ingestion/0.1"
    )
    DEFAULT_MAX_REDIRECTS = 5

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        timeout_seconds: float = (
            DEFAULT_TIMEOUT_SECONDS
        ),
        max_response_bytes: int = (
            DEFAULT_MAX_RESPONSE_BYTES
        ),
        user_agent: str = (
            DEFAULT_USER_AGENT
        ),
        max_redirects: int = (
            DEFAULT_MAX_REDIRECTS
        ),
        resolver: HostResolver | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be "
                "greater than zero"
            )
        if max_response_bytes <= 0:
            raise ValueError(
                "max_response_bytes must be "
                "greater than zero"
            )
        if not user_agent.strip():
            raise ValueError(
                "user_agent must not be empty"
            )
        if max_redirects < 0:
            raise ValueError(
                "max_redirects must not be negative"
            )

        self._client = (
            client
            or httpx.Client(
                trust_env=False
            )
        )
        self._owns_client = (
            client is None
        )
        self._timeout = httpx.Timeout(
            timeout_seconds
        )
        self._max_response_bytes = (
            max_response_bytes
        )
        self._user_agent = user_agent
        self._max_redirects = (
            max_redirects
        )
        self._url_policy = (
            FeedUrlPolicy(
                resolver=resolver
            )
            if resolver is not None
            else FeedUrlPolicy()
        )

    def fetch(
        self,
        request: FeedFetchRequest,
    ) -> FeedFetchResult:
        requested_url = (
            request.url.strip()
        )
        current_url = requested_url
        redirect_count = 0

        while True:
            target = (
                self._url_policy.resolve(
                    current_url
                )
            )

            headers = {
                "Accept": (
                    "application/atom+xml, "
                    "application/rss+xml, "
                    "application/xml;q=0.9, "
                    "text/xml;q=0.9, "
                    "*/*;q=0.1"
                ),
                "User-Agent": (
                    self._user_agent
                ),
                "Host": (
                    target.host_header
                ),
            }
            if request.etag:
                headers[
                    "If-None-Match"
                ] = request.etag
            if request.last_modified:
                headers[
                    "If-Modified-Since"
                ] = (
                    request.last_modified
                )

            try:
                with self._client.stream(
                    "GET",
                    target.connect_url,
                    headers=headers,
                    timeout=self._timeout,
                    follow_redirects=False,
                    extensions={
                        "sni_hostname": (
                            target.sni_hostname
                        )
                    },
                ) as response:
                    if (
                        response.is_redirect
                        and response.headers.get(
                            "location"
                        )
                    ):
                        if (
                            redirect_count
                            >= self._max_redirects
                        ):
                            raise FeedConnectionError(
                                "Feed redirect limit "
                                "exceeded."
                            )

                        current_url = urljoin(
                            target.logical_url,
                            response.headers[
                                "location"
                            ],
                        )
                        redirect_count += 1
                        continue

                    if (
                        response.status_code
                        == 304
                    ):
                        return self._result(
                            request=request,
                            response=response,
                            content=None,
                            final_url=(
                                target.logical_url
                            ),
                        )

                    try:
                        response.raise_for_status()
                    except (
                        httpx.HTTPStatusError
                    ) as exc:
                        raise FeedHttpStatusError(
                            url=(
                                target.logical_url
                            ),
                            status_code=(
                                response.status_code
                            ),
                        ) from exc

                    content = (
                        self._read_limited(
                            response
                        )
                    )
                    return self._result(
                        request=request,
                        response=response,
                        content=content,
                        final_url=(
                            target.logical_url
                        ),
                    )
            except FeedHttpStatusError:
                raise
            except (
                FeedResponseTooLargeError
            ):
                raise
            except InvalidFeedUrlError:
                raise
            except FeedConnectionError:
                raise
            except (
                httpx.TimeoutException
            ) as exc:
                raise FeedTimeoutError(
                    "Feed request to "
                    f"{current_url!r} timed out."
                ) from exc
            except (
                httpx.InvalidURL,
                httpx.UnsupportedProtocol,
            ) as exc:
                raise InvalidFeedUrlError(
                    "Invalid feed URL: "
                    f"{current_url!r}."
                ) from exc
            except (
                httpx.RequestError
            ) as exc:
                raise FeedConnectionError(
                    "Feed request to "
                    f"{current_url!r} failed: "
                    f"{type(exc).__name__}."
                ) from exc

    def _read_limited(
        self,
        response: httpx.Response,
    ) -> bytes:
        declared_length = (
            response.headers.get(
                "content-length"
            )
        )
        if declared_length:
            try:
                if (
                    int(declared_length)
                    > self._max_response_bytes
                ):
                    raise (
                        FeedResponseTooLargeError(
                            "Feed response exceeds "
                            "configured byte limit."
                        )
                    )
            except ValueError:
                pass

        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if (
                len(body)
                > self._max_response_bytes
            ):
                raise FeedResponseTooLargeError(
                    "Feed response exceeds "
                    "configured byte limit."
                )
        return bytes(body)

    @staticmethod
    def _result(
        *,
        request: FeedFetchRequest,
        response: httpx.Response,
        content: bytes | None,
        final_url: str,
    ) -> FeedFetchResult:
        return FeedFetchResult(
            requested_url=(
                request.url.strip()
            ),
            final_url=final_url,
            status_code=(
                response.status_code
            ),
            content=content,
            content_type=(
                response.headers.get(
                    "content-type"
                )
            ),
            etag=(
                response.headers.get(
                    "etag"
                )
                or request.etag
            ),
            last_modified=(
                response.headers.get(
                    "last-modified"
                )
                or request.last_modified
            ),
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(
        self,
    ) -> "FeedFetcher":
        return self

    def __exit__(
        self,
        exc_type: (
            type[BaseException]
            | None
        ),
        exc_value: (
            BaseException
            | None
        ),
        traceback: (
            TracebackType
            | None
        ),
    ) -> None:
        self.close()
