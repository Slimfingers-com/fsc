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
    ResolvedFeedTarget,
)


class FeedFetcher:
    """Synchronous HTTP client for RSS and Atom feeds."""

    DEFAULT_TIMEOUT_SECONDS = 15.0
    DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024
    DEFAULT_USER_AGENT = "FSC-Feed-Ingestion/0.1"
    DEFAULT_MAX_REDIRECTS = 5
    _REDIRECT_STATUSES = {
        301,
        302,
        303,
        307,
        308,
    }

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        user_agent: str = DEFAULT_USER_AGENT,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        url_policy: FeedUrlPolicy | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero"
            )
        if max_response_bytes <= 0:
            raise ValueError(
                "max_response_bytes must be greater than zero"
            )
        if not user_agent.strip():
            raise ValueError(
                "user_agent must not be empty"
            )
        if max_redirects < 0:
            raise ValueError(
                "max_redirects must not be negative"
            )

        self._client = client or httpx.Client(
            trust_env=False,
        )
        self._owns_client = client is None
        self._timeout = httpx.Timeout(
            timeout_seconds
        )
        self._max_response_bytes = (
            max_response_bytes
        )
        self._user_agent = user_agent
        self._max_redirects = max_redirects
        self._url_policy = (
            url_policy or FeedUrlPolicy()
        )

    def fetch(
        self,
        request: FeedFetchRequest,
    ) -> FeedFetchResult:
        requested_url = request.url.strip()
        target = self._url_policy.resolve(
            requested_url
        )
        redirects = 0

        base_headers = {
            "Accept": (
                "application/atom+xml, "
                "application/rss+xml, "
                "application/xml;q=0.9, "
                "text/xml;q=0.9, */*;q=0.1"
            ),
            "User-Agent": self._user_agent,
        }
        if request.etag:
            base_headers[
                "If-None-Match"
            ] = request.etag
        if request.last_modified:
            base_headers[
                "If-Modified-Since"
            ] = request.last_modified

        while True:
            try:
                response = self._request(
                    target,
                    base_headers=base_headers,
                )
            except (
                FeedHttpStatusError,
                FeedResponseTooLargeError,
                InvalidFeedUrlError,
            ):
                raise
            except httpx.TimeoutException as exc:
                raise FeedTimeoutError(
                    "Feed request to "
                    f"{target.logical_url!r} "
                    "timed out."
                ) from exc
            except httpx.RequestError as exc:
                raise FeedConnectionError(
                    "Feed request to "
                    f"{target.logical_url!r} "
                    f"failed: {exc}."
                ) from exc

            if (
                response.status_code
                in self._REDIRECT_STATUSES
            ):
                location = response.headers.get(
                    "location"
                )
                response.close()

                if not location:
                    raise FeedHttpStatusError(
                        url=target.logical_url,
                        status_code=(
                            response.status_code
                        ),
                    )

                if (
                    redirects
                    >= self._max_redirects
                ):
                    raise FeedConnectionError(
                        "Feed request exceeded "
                        "the redirect limit."
                    )

                redirect_url = urljoin(
                    target.logical_url,
                    location,
                )
                target = (
                    self._url_policy.resolve(
                        redirect_url
                    )
                )
                redirects += 1
                continue

            return self._consume_response(
                response,
                request=request,
                requested_url=requested_url,
                final_url=target.logical_url,
            )

    def _request(
        self,
        target: ResolvedFeedTarget,
        *,
        base_headers: dict[str, str],
    ) -> httpx.Response:
        headers = {
            **base_headers,
            "Host": target.host_header,
        }
        request = self._client.build_request(
            "GET",
            target.connect_url,
            headers=headers,
            timeout=self._timeout,
            extensions={
                "sni_hostname": (
                    target.sni_hostname
                ),
            },
        )
        return self._client.send(
            request,
            stream=True,
            follow_redirects=False,
        )

    def _consume_response(
        self,
        response: httpx.Response,
        *,
        request: FeedFetchRequest,
        requested_url: str,
        final_url: str,
    ) -> FeedFetchResult:
        try:
            if response.status_code == 304:
                return self._result(
                    request=request,
                    requested_url=(
                        requested_url
                    ),
                    final_url=final_url,
                    response=response,
                    content=None,
                )

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise FeedHttpStatusError(
                    url=final_url,
                    status_code=(
                        response.status_code
                    ),
                ) from exc

            content = self._read_limited(
                response
            )
            return self._result(
                request=request,
                requested_url=requested_url,
                final_url=final_url,
                response=response,
                content=content,
            )
        finally:
            response.close()

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
                            "Feed response "
                            "exceeds configured "
                            "byte limit."
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
                raise (
                    FeedResponseTooLargeError(
                        "Feed response "
                        "exceeds configured "
                        "byte limit."
                    )
                )
        return bytes(body)

    @staticmethod
    def _result(
        *,
        request: FeedFetchRequest,
        requested_url: str,
        final_url: str,
        response: httpx.Response,
        content: bytes | None,
    ) -> FeedFetchResult:
        return FeedFetchResult(
            requested_url=requested_url,
            final_url=final_url,
            status_code=response.status_code,
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
            type[BaseException] | None
        ),
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
