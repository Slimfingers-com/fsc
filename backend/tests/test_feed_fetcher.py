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
from app.ingestion.url_policy import (
    FeedUrlPolicy,
)


PUBLIC_IP = "93.184.216.34"
SECOND_PUBLIC_IP = "142.250.74.14"


def public_policy(
    mapping: dict[
        str,
        tuple[str, ...],
    ]
    | None = None,
) -> FeedUrlPolicy:
    hosts = mapping or {
        "example.com": (
            PUBLIC_IP,
        ),
    }

    def resolver(
        hostname: str,
        port: int,
    ) -> tuple[str, ...]:
        del port
        return hosts.get(
            hostname,
            (PUBLIC_IP,),
        )

    return FeedUrlPolicy(
        resolver=resolver
    )


def fetcher(
    client: httpx.Client,
    **kwargs,
) -> FeedFetcher:
    return FeedFetcher(
        client,
        url_policy=public_policy(),
        **kwargs,
    )


def test_fetch_returns_payload_and_metadata():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.headers["user-agent"]
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
        result = fetcher(
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
        result = fetcher(
            client
        ).fetch(
            FeedFetchRequest(
                "https://example.com/feed.xml",
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
            fetcher(
                client
            ).fetch(
                FeedFetchRequest(
                    "https://example.com/missing"
                )
            )
    assert exc.value.status_code == 404


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
            fetcher(
                client
            ).fetch(
                FeedFetchRequest(
                    "https://example.com/feed"
                )
            )


def test_fetch_maps_connection_error():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "failed",
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        with pytest.raises(
            FeedConnectionError
        ):
            fetcher(
                client
            ).fetch(
                FeedFetchRequest(
                    "https://example.com/feed"
                )
            )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "ftp://example.com/feed",
        "not-a-url",
        "https://user:secret@example.com/feed",
    ],
)
def test_fetch_rejects_invalid_urls(
    url: str,
):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: None
        )
    ) as client:
        with pytest.raises(
            InvalidFeedUrlError
        ):
            fetcher(
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
        "http://10.0.0.1/feed",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/feed",
        "http://[fc00::1]/feed",
    ],
)
def test_fetch_rejects_non_public_literal_addresses(
    url: str,
):
    called = False

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(
            200,
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
            fetcher(
                client
            ).fetch(
                FeedFetchRequest(
                    url
                )
            )

    assert not called


def test_fetch_rejects_hostname_resolving_only_to_private_addresses():
    policy = public_policy(
        {
            "internal.example": (
                "10.0.0.5",
                "192.168.1.20",
            )
        }
    )
    called = False

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(
            200,
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
                url_policy=policy,
            ).fetch(
                FeedFetchRequest(
                    "https://internal.example/feed"
                )
            )

    assert not called


def test_redirect_target_is_revalidated_and_private_redirect_is_blocked():
    calls: list[str] = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        calls.append(
            request.url.host
        )
        return httpx.Response(
            302,
            headers={
                "location": (
                    "http://127.0.0.1/admin"
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
            fetcher(
                client
            ).fetch(
                FeedFetchRequest(
                    "https://example.com/feed"
                )
            )

    assert calls == [
        PUBLIC_IP
    ]


def test_public_redirect_is_pinned_again_and_preserves_logical_url():
    policy = public_policy(
        {
            "example.com": (
                PUBLIC_IP,
            ),
            "cdn.example.net": (
                SECOND_PUBLIC_IP,
            ),
        }
    )
    calls: list[
        tuple[
            str,
            str,
            str | None,
        ]
    ] = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        calls.append(
            (
                request.url.host,
                request.headers["host"],
                request.extensions.get(
                    "sni_hostname"
                ),
            )
        )
        if (
            request.url.host
            == PUBLIC_IP
        ):
            return httpx.Response(
                302,
                headers={
                    "location": (
                        "https://cdn.example.net/final.xml"
                    )
                },
                request=request,
            )
        return httpx.Response(
            200,
            content=b"<rss/>",
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        result = FeedFetcher(
            client,
            url_policy=policy,
        ).fetch(
            FeedFetchRequest(
                "https://example.com/feed"
            )
        )

    assert calls == [
        (
            PUBLIC_IP,
            "example.com",
            "example.com",
        ),
        (
            SECOND_PUBLIC_IP,
            "cdn.example.net",
            "cdn.example.net",
        ),
    ]
    assert (
        result.final_url
        == "https://cdn.example.net/final.xml"
    )


def test_fetch_enforces_redirect_limit():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            302,
            headers={
                "location": (
                    "https://example.com/again"
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
            fetcher(
                client,
                max_redirects=1,
            ).fetch(
                FeedFetchRequest(
                    "https://example.com/feed"
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
            fetcher(
                client,
                max_response_bytes=4,
            ).fetch(
                FeedFetchRequest(
                    "https://example.com/feed"
                )
            )



def test_fetch_prefers_public_ipv4_when_dns_returns_both_families():
    def resolver(
        hostname: str,
        port: int,
    ):
        assert hostname == "example.com"
        return (
            "2606:4700:4700::1111",
            "1.1.1.1",
        )

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.host == "1.1.1.1"
        return httpx.Response(
            200,
            content=b"<rss/>",
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        FeedFetcher(
            client,
            resolver=resolver,
        ).fetch(
            FeedFetchRequest(
                "https://example.com/feed"
            )
        )


def test_fetch_normalizes_unicode_hostname_to_idna():
    def resolver(
        hostname: str,
        port: int,
    ):
        assert (
            hostname
            == "xn--bcher-kva.example"
        )
        return ("1.1.1.1",)

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.headers["host"]
            == "xn--bcher-kva.example"
        )
        assert (
            request.extensions[
                "sni_hostname"
            ]
            == "xn--bcher-kva.example"
        )
        return httpx.Response(
            200,
            content=b"<rss/>",
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(
            handler
        )
    ) as client:
        FeedFetcher(
            client,
            resolver=resolver,
        ).fetch(
            FeedFetchRequest(
                "https://bücher.example/feed"
            )
        )
