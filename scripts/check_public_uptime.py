"""Validate fully rendered public pages (including Next.js error HTML with HTTP 200).

A network-only retry does not recover a successful HTTP response containing
the Next.js error boundary. Retry the *whole* page, and fail on persistent errors.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://fsc.eu"
ATTEMPTS = 3
TIMEOUT_SECONDS = 25
MAX_HTML_BYTES = 5_000_000


@dataclass(frozen=True)
class Page:
    name: str
    path: str
    landmarks: tuple[tuple[str, str, str], ...]


PAGES = (
    Page("Startseite", "/", (("h1", "id", "home-title"), ("form", "role", "search"))),
    Page("Ereignisse", "/stories", (("select", "id", "story-sort"), ("select", "id", "story-sources"))),
)


class LandmarkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: set[tuple[str, str, str]] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value is not None:
                self.tags.add((tag, key, value))


class PageCheckError(Exception):
    """No valid rendered page was returned."""


def check_html(page: Page, html: bytes) -> None:
    if len(html) > MAX_HTML_BYTES:
        raise PageCheckError("HTML document exceeded safe maximum size")
    parser = LandmarkParser()
    parser.feed(html.decode("utf-8", "replace"))
    if ("html", "lang", "de") not in parser.tags:
        raise PageCheckError("German HTML document missing")
    for tag, key, value in page.landmarks:
        if (tag, key, value) not in parser.tags:
            raise PageCheckError(f"rendered {tag}[{key}={value}] missing")


def fetch_html(url: str) -> bytes:
    request = Request(url, headers={"Accept": "text/html", "User-Agent": "FSC-production-uptime/2"})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise PageCheckError(f"HTTP {response.status}")
        payload = response.read(MAX_HTML_BYTES + 1)
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            raise PageCheckError(f"unexpected content type {content_type!r}")
        return payload


def check_page(page: Page, *, fetch=fetch_html, sleep=time.sleep, output=print) -> bool:
    url = BASE_URL + page.path
    for attempt in range(1, ATTEMPTS + 1):
        try:
            check_html(page, fetch(url))
        except (PageCheckError, HTTPError, URLError, TimeoutError, OSError, UnicodeError) as exc:
            reason = f"{type(exc).__name__}: {exc}"
            if attempt == ATTEMPTS:
                output(f"::error title=Production uptime::{page.name} {url} failed {ATTEMPTS} times; last error: {reason}")
                return False
            output(f"::warning title=Transient page failure::{page.name} attempt {attempt}/{ATTEMPTS}: {reason}; retrying complete page")
            sleep(3 * attempt)
        else:
            if attempt > 1:
                output(f"{page.name}: recovered after {attempt} complete page requests")
            else:
                output(f"{page.name}: HTML and content OK")
            return True
    return False


def main() -> int:
    healthy = [check_page(page) for page in PAGES]
    if all(healthy):
        print("Production uptime OK: public pages fully rendered in German.")
        return 0
    print("Production uptime FAILED: one or more pages did not recover.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
