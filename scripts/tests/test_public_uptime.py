"""Offline regressions for the external uptime monitor."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_public_uptime import PAGES, PageCheckError, check_html, check_page  # noqa: E402

HOME = b'<html lang="de"><body><h1 id="home-title">News</h1><form role="search"></form></body></html>'
STORIES = b'<html lang="de"><select id="story-sort"></select><select id="story-sources"></select></html>'


class UptimeMonitorTests(unittest.TestCase):
    def test_valid_html_pages(self) -> None:
        check_html(PAGES[0], HOME)
        check_html(PAGES[1], STORIES)

    def test_html_200_with_next_error_boundary_is_not_healthy(self) -> None:
        with self.assertRaisesRegex(PageCheckError, "rendered h1"):
            check_html(PAGES[0], b'<html lang="de"><h1>Die Daten konnten nicht geladen werden.</h1></html>')

    def test_reject_wrong_language_and_missing_story_elements(self) -> None:
        with self.assertRaisesRegex(PageCheckError, "German HTML"):
            check_html(PAGES[0], HOME.replace(b'lang="de"', b'lang="en"'))
        with self.assertRaisesRegex(PageCheckError, "story-sources"):
            check_html(PAGES[1], STORIES.replace(b'id="story-sources"', b'id="other"'))

    def test_retries_entire_page_after_broken_http_200(self) -> None:
        requests = []
        outputs = []
        sleeps = []
        def fetch(url: str) -> bytes:
            requests.append(url)
            return HOME if len(requests) == 2 else b'<html lang="de"><h1>Serverfehler</h1></html>'
        self.assertTrue(check_page(PAGES[0], fetch=fetch, sleep=sleeps.append, output=outputs.append))
        self.assertEqual(len(requests), 2)
        self.assertEqual(sleeps, [3])
        self.assertTrue(any("recovered" in output for output in outputs))

    def test_persistent_error_fails_after_three_requests(self) -> None:
        requests = []
        outputs = []
        sleeps = []
        def fetch(url: str) -> bytes:
            requests.append(url)
            return b'<html lang="de"><h1>Fehler</h1></html>'
        self.assertFalse(check_page(PAGES[0], fetch=fetch, sleep=sleeps.append, output=outputs.append))
        self.assertEqual(len(requests), 3)
        self.assertEqual(sleeps, [3, 6])
        self.assertIn("::error", outputs[-1])

    def test_not_confused_by_a_marker_in_an_embedded_script(self) -> None:
        with self.assertRaisesRegex(PageCheckError, "rendered h1"):
            check_html(PAGES[0], b'<html lang="de"><script>const text = "home-title";</script><form role="search"></form></html>')


if __name__ == "__main__":
    unittest.main()
