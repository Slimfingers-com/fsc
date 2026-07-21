import httpx
import pytest

from app.ingestion import (
    FeedConnectionError,
    FeedFetchRequest,
    FeedFetcher,
    FeedHttpStatusError,
    FeedResponseTooLargeError,
    FeedTimeoutError,
    InvalidFeedUrlError,
)


def test_fetch_returns_payload_and_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"] == "test-agent"
        return httpx.Response(
            200,
            headers={"content-type": "application/rss+xml", "etag": '"v2"'},
            content=b"<rss version='2.0'></rss>",
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = FeedFetcher(client, user_agent="test-agent").fetch(
            FeedFetchRequest("https://example.com/feed.xml")
        )

    assert result.status_code == 200
    assert result.etag == '"v2"'
    assert result.content == b"<rss version='2.0'></rss>"


def test_fetch_uses_conditional_headers_and_accepts_304():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["if-none-match"] == '"v1"'
        assert request.headers["if-modified-since"] == "Tue, 21 Jul 2026 10:00:00 GMT"
        return httpx.Response(304, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = FeedFetcher(client).fetch(
            FeedFetchRequest(
                "https://example.com/feed.xml",
                etag='"v1"',
                last_modified="Tue, 21 Jul 2026 10:00:00 GMT",
            )
        )

    assert result.not_modified
    assert result.content is None
    assert result.etag == '"v1"'


def test_fetch_maps_http_status_error():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(404, request=request)
        )
    ) as client:
        with pytest.raises(FeedHttpStatusError) as exc:
            FeedFetcher(client).fetch(FeedFetchRequest("https://example.com/missing"))
    assert exc.value.status_code == 404


def test_fetch_maps_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(FeedTimeoutError):
            FeedFetcher(client).fetch(FeedFetchRequest("https://example.com/feed"))


def test_fetch_maps_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("failed", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(FeedConnectionError):
            FeedFetcher(client).fetch(FeedFetchRequest("https://example.com/feed"))


@pytest.mark.parametrize("url", ["", "ftp://example.com/feed", "not-a-url"])
def test_fetch_rejects_invalid_urls(url: str):
    with httpx.Client(transport=httpx.MockTransport(lambda request: None)) as client:
        with pytest.raises(InvalidFeedUrlError):
            FeedFetcher(client).fetch(FeedFetchRequest(url))


def test_fetch_rejects_oversized_response():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"12345", request=request)
        )
    ) as client:
        with pytest.raises(FeedResponseTooLargeError):
            FeedFetcher(client, max_response_bytes=4).fetch(
                FeedFetchRequest("https://example.com/feed")
            )
