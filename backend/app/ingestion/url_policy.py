from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit

from app.ingestion.exceptions import (
    FeedConnectionError,
    InvalidFeedUrlError,
)


HostResolver = Callable[
    [str, int],
    Iterable[str],
]


def system_host_resolver(
    hostname: str,
    port: int,
) -> tuple[str, ...]:
    try:
        results = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise FeedConnectionError(
            f"Could not resolve feed host {hostname!r}."
        ) from exc

    addresses = tuple(
        dict.fromkeys(
            result[4][0]
            for result in results
        )
    )
    if not addresses:
        raise FeedConnectionError(
            f"Feed host {hostname!r} resolved to no addresses."
        )
    return addresses


@dataclass(
    frozen=True,
    slots=True,
)
class ResolvedFeedTarget:
    logical_url: str
    connect_url: str
    host_header: str
    sni_hostname: str


class FeedUrlPolicy:
    def __init__(
        self,
        *,
        resolver: HostResolver
        = system_host_resolver,
    ) -> None:
        self._resolver = resolver

    def resolve(
        self,
        url: str,
    ) -> ResolvedFeedTarget:
        parsed = self._parse(url)
        raw_hostname = parsed.hostname
        assert raw_hostname is not None
        hostname = self._ascii_hostname(
            raw_hostname
        )

        try:
            port = parsed.port
        except ValueError as exc:
            raise InvalidFeedUrlError(
                f"Invalid feed URL port: {url!r}."
            ) from exc

        if port is None:
            port = (
                443
                if parsed.scheme.lower()
                == "https"
                else 80
            )

        addresses = (
            self._literal_address(
                hostname
            )
            or tuple(
                self._resolver(
                    hostname,
                    port,
                )
            )
        )

        public_addresses = [
            address
            for address in addresses
            if self._is_public_ip(
                address
            )
        ]
        public_addresses.sort(
            key=lambda address: (
                ipaddress.ip_address(
                    address
                ).version
                != 4
            )
        )
        public_address = (
            public_addresses[0]
            if public_addresses
            else None
        )
        if public_address is None:
            raise InvalidFeedUrlError(
                "Feed URL resolves only to "
                "non-public network addresses."
            )

        connect_host = (
            f"[{public_address}]"
            if ":" in public_address
            else public_address
        )
        connect_netloc = (
            f"{connect_host}:{port}"
        )
        path = parsed.path or "/"
        connect_url = urlunsplit(
            (
                parsed.scheme.lower(),
                connect_netloc,
                path,
                parsed.query,
                "",
            )
        )

        host_header = self._host_header(
            parsed,
            hostname=hostname,
        )
        logical_url = urlunsplit(
            (
                parsed.scheme.lower(),
                parsed.netloc,
                path,
                parsed.query,
                "",
            )
        )

        return ResolvedFeedTarget(
            logical_url=logical_url,
            connect_url=connect_url,
            host_header=host_header,
            sni_hostname=hostname,
        )

    @staticmethod
    def _parse(
        url: str,
    ) -> SplitResult:
        stripped = url.strip()
        if not stripped:
            raise InvalidFeedUrlError(
                "Feed URL must not be empty."
            )

        try:
            parsed = urlsplit(
                stripped
            )
        except ValueError as exc:
            raise InvalidFeedUrlError(
                f"Invalid feed URL: {stripped!r}."
            ) from exc

        if (
            parsed.scheme.lower()
            not in {"http", "https"}
            or not parsed.netloc
            or parsed.hostname is None
        ):
            raise InvalidFeedUrlError(
                f"Invalid feed URL: {stripped!r}."
            )

        if (
            parsed.username is not None
            or parsed.password is not None
        ):
            raise InvalidFeedUrlError(
                "Feed URLs must not contain credentials."
            )

        return parsed

    @staticmethod
    def _ascii_hostname(
        hostname: str,
    ) -> str:
        if "%" in hostname:
            raise InvalidFeedUrlError(
                "Scoped IP addresses are not allowed "
                "for feed URLs."
            )

        try:
            return str(
                ipaddress.ip_address(
                    hostname
                )
            )
        except ValueError:
            pass

        try:
            return hostname.encode(
                "idna"
            ).decode(
                "ascii"
            )
        except UnicodeError as exc:
            raise InvalidFeedUrlError(
                "Feed URL contains an invalid hostname."
            ) from exc

    @staticmethod
    def _literal_address(
        hostname: str,
    ) -> tuple[str, ...] | None:
        candidate = hostname
        if "%" in candidate:
            raise InvalidFeedUrlError(
                "Scoped IP addresses are not allowed "
                "for feed URLs."
            )

        try:
            address = ipaddress.ip_address(
                candidate
            )
        except ValueError:
            return None
        return (str(address),)

    @staticmethod
    def _is_public_ip(
        value: str,
    ) -> bool:
        if "%" in value:
            return False
        try:
            return ipaddress.ip_address(
                value
            ).is_global
        except ValueError:
            return False

    @staticmethod
    def _host_header(
        parsed: SplitResult,
        *,
        hostname: str,
    ) -> str:
        host = (
            f"[{hostname}]"
            if ":" in hostname
            else hostname
        )

        try:
            port = parsed.port
        except ValueError as exc:
            raise InvalidFeedUrlError(
                "Feed URL contains an invalid port."
            ) from exc

        if port is None:
            return host

        default_port = (
            443
            if parsed.scheme.lower()
            == "https"
            else 80
        )
        return (
            host
            if port == default_port
            else f"{host}:{port}"
        )
