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


PUBLIC_IP = "93.184.216.34"


def public_resolver(
    hostname: str,
    port: int,
):
    assert port in {80, 443}
    return (PUBLIC_IP,)


def make_fetcher(
    client: httpx.Client,
    **kwargs,
) -> FeedFetcher:
    return FeedFetcher(
        client,
        resolver=public_resolver,
        **kwargs,
    )


def test_fetch_returns_payload_and_metadata():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.headers[
                "user-agent"
            ]
            == "test-agent"
        )
        assert (
            request.headers["host"]
            == "example.com"
        )
        assert (
            request.url.host
            == PUBLIC_IP
        )
        assert (
            request.extensions[
                "sni_hostname"
            ]
            == "example.com"
        )
        return httpx.Response(
            200,
            headers={
                "content-type": (
                    "application/rss+xml"
                ),
                "etag": '"v2"',
            },
            content=(
                b"<rss version='2.0'></rss>"
            ),
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        result = make_fetcher(
            client,
            user_agent="test-agent",
        ).fetch(
            FeedFetchRequest(
                "https://example.com/feed.xml"
            )
        )

    assert result.status_code == 200
    assert result.etag == '"v2"'
    assert (
        result.content
        == b"<rss version='2.0'></rss>"
    )
    assert (
        result.final_url
        == "https://example.com/feed.xml"
    )


def test_fetch_uses_conditional_headers_and_accepts_304():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.headers[
                "if-none-match"
            ]
            == '"v1"'
        )
        assert (
            request.headers[
                "if-modified-since"
            ]
            == (
                "Tue, 21 Jul 2026 "
                "10:00:00 GMT"
            )
        )
        return httpx.Response(
            304,
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        result = make_fetcher(
            client
        ).fetch(
            FeedFetchRequest(
                (
                    "https://example.com/"
                    "feed.xml"
                ),
                etag='"v1"',
                last_modified=(
                    "Tue, 21 Jul 2026 "
                    "10:00:00 GMT"
                ),
            )
        )

    assert result.not_modified
    assert result.content is None
    assert result.etag == '"v1"'


def test_fetch_maps_http_status_error():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: (
                httpx.Response(
                    404,
                    request=request,
                )
            )
        )
    ) as client:
        with pytest.raises(
            FeedHttpStatusError
        ) as exc:
            make_fetcher(
                client
            ).fetch(
                FeedFetchRequest(
                    (
                        "https://example.com/"
                        "missing"
                    )
                )
            )
    assert (
        exc.value.status_code
        == 404
    )
    assert (
        exc.value.url
        == (
            "https://example.com/"
            "missing"
        )
    )


def test_fetch_maps_timeout():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ReadTimeout(
            "timeout",
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        with pytest.raises(
            FeedTimeoutError
        ):
            make_fetcher(
                client
            ).fetch(
                FeedFetchRequest(
                    (
                        "https://example.com/"
                        "feed"
                    )
                )
            )


def test_fetch_maps_connection_error_without_leaking_detail():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "sensitive resolver detail",
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        with pytest.raises(
            FeedConnectionError
        ) as exc:
            make_fetcher(
                client
            ).fetch(
                FeedFetchRequest(
                    (
                        "https://example.com/"
                        "feed"
                    )
                )
            )

    assert (
        "sensitive resolver detail"
        not in str(exc.value)
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "ftp://example.com/feed",
        "not-a-url",
        (
            "https://user:secret@"
            "example.com/feed"
        ),
    ],
)
def test_fetch_rejects_invalid_urls(
    url: str,
):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: (
                httpx.Response(
                    200,
                    request=request,
                )
            )
        )
    ) as client:
        with pytest.raises(
            InvalidFeedUrlError
        ):
            make_fetcher(
                client
            ).fetch(
                FeedFetchRequest(
                    url
                )
            )


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/feed",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/feed",
        "http://192.168.1.1/feed",
        "http://[::1]/feed",
        "http://[fe80::1]/feed",
    ],
)
def test_fetch_rejects_non_public_literal_addresses(
    url: str,
):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: (
                pytest.fail(
                    "request must not be sent"
                )
            )
        )
    ) as client:
        with pytest.raises(
            InvalidFeedUrlError
        ):
            FeedFetcher(
                client
            ).fetch(
                FeedFetchRequest(
                    url
                )
            )


def test_fetch_rejects_hostname_resolving_only_to_private_addresses():
    def private_resolver(
        hostname: str,
        port: int,
    ):
        assert hostname == "internal.test"
        assert port == 80
        return (
            "127.0.0.1",
            "10.0.0.5",
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: (
                pytest.fail(
                    "request must not be sent"
                )
            )
        )
    ) as client:
        with pytest.raises(
            InvalidFeedUrlError
        ):
            FeedFetcher(
                client,
                resolver=private_resolver,
            ).fetch(
                FeedFetchRequest(
                    (
                        "http://internal.test/"
                        "feed"
                    )
                )
            )


def test_fetch_revalidates_redirect_targets():
    requests = 0

    def resolver(
        hostname: str,
        port: int,
    ):
        if hostname == "example.com":
            return (PUBLIC_IP,)
        if hostname == "internal.test":
            return ("169.254.169.254",)
        raise AssertionError(
            hostname
        )

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(
            302,
            headers={
                "location": (
                    "http://internal.test/"
                    "feed"
                )
            },
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        with pytest.raises(
            InvalidFeedUrlError
        ):
            FeedFetcher(
                client,
                resolver=resolver,
            ).fetch(
                FeedFetchRequest(
                    (
                        "https://example.com/"
                        "feed"
                    )
                )
            )

    assert requests == 1


def test_fetch_follows_public_redirect_and_preserves_logical_final_url():
    seen_hosts = []

    def resolver(
        hostname: str,
        port: int,
    ):
        if hostname == "example.com":
            return ("93.184.216.34",)
        if hostname == "cdn.example.net":
            return ("203.0.113.10",)
        raise AssertionError(
            hostname
        )

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        seen_hosts.append(
            request.headers["host"]
        )
        if (
            request.headers["host"]
            == "example.com"
        ):
            return httpx.Response(
                301,
                headers={
                    "location": (
                        "https://cdn.example.net/"
                        "feed.xml"
                    )
                },
                request=request,
            )

        return httpx.Response(
            200,
            content=b"<rss/>",
            request=request,
        )

    # 8.8.8.8 is used for the test-only public
    # address because TEST-NET ranges are non-global
    # according to Python's ipaddress module.
    def public_redirect_resolver(
        hostname: str,
        port: int,
    ):
        if hostname == "example.com":
            return ("8.8.8.8",)
        if hostname == "cdn.example.net":
            return ("1.1.1.1",)
        raise AssertionError(
            hostname
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        result = FeedFetcher(
            client,
            resolver=public_redirect_resolver,
        ).fetch(
            FeedFetchRequest(
                (
                    "https://example.com/"
                    "feed"
                )
            )
        )

    assert seen_hosts == [
        "example.com",
        "cdn.example.net",
    ]
    assert (
        result.final_url
        == (
            "https://cdn.example.net/"
            "feed.xml"
        )
    )


def test_fetch_enforces_redirect_limit():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            302,
            headers={
                "location": (
                    "https://example.com/"
                    "next"
                )
            },
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        with pytest.raises(
            FeedConnectionError,
            match="redirect limit",
        ):
            make_fetcher(
                client,
                max_redirects=1,
            ).fetch(
                FeedFetchRequest(
                    (
                        "https://example.com/"
                        "feed"
                    )
                )
            )


def test_fetch_rejects_oversized_response():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: (
                httpx.Response(
                    200,
                    content=b"12345",
                    request=request,
                )
            )
        )
    ) as client:
        with pytest.raises(
            FeedResponseTooLargeError
        ):
            make_fetcher(
                client,
                max_response_bytes=4,
            ).fetch(
                FeedFetchRequest(
                    (
                        "https://example.com/"
                        "feed"
                    )
                )
            )
