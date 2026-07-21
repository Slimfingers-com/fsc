from datetime import datetime, timezone

import pytest

from app.ingestion import (
    EmptyFeedError,
    FeedFetchResult,
    FeedFormat,
    FeedParser,
    UnsupportedFeedFormatError,
)


def fetched(content: bytes | None, status_code: int = 200) -> FeedFetchResult:
    return FeedFetchResult(
        requested_url="https://example.com/original",
        final_url="https://example.com/feed",
        status_code=status_code,
        content=content,
        content_type="application/xml",
        etag=None,
        last_modified=None,
    )


def test_parse_rss2():
    xml = b'''<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <title>Example News</title>
      <link>https://example.com/</link>
      <description>News description</description>
      <lastBuildDate>Tue, 21 Jul 2026 10:30:00 GMT</lastBuildDate>
      <item>
        <guid>article-1</guid><title>First</title>
        <link>https://example.com/1</link>
        <description>Summary</description>
        <pubDate>Tue, 21 Jul 2026 09:00:00 GMT</pubDate>
        <category>Politics</category>
        <enclosure url="https://example.com/audio.mp3" type="audio/mpeg" length="123"/>
      </item>
    </channel></rss>'''

    feed = FeedParser().parse(fetched(xml))
    assert feed.format is FeedFormat.RSS
    assert feed.title == "Example News"
    assert feed.updated_at == datetime(2026, 7, 21, 10, 30, tzinfo=timezone.utc)
    assert len(feed.entries) == 1
    entry = feed.entries[0]
    assert entry.external_id == "article-1"
    assert entry.categories == ("Politics",)
    assert entry.enclosures[0].length_bytes == 123


def test_parse_atom():
    xml = b'''<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Example Atom</title>
      <link rel="alternate" href="https://example.com/"/>
      <updated>2026-07-21T10:30:00Z</updated>
      <entry>
        <id>tag:example.com,2026:2</id><title>Second</title>
        <link href="https://example.com/2"/>
        <summary type="html">&lt;p&gt;Summary&lt;/p&gt;</summary>
        <content type="html">&lt;p&gt;Content&lt;/p&gt;</content>
        <author><name>Jane Doe</name></author>
        <published>2026-07-21T09:00:00+02:00</published>
        <category term="Technology"/><category term="AI"/>
      </entry>
    </feed>'''

    feed = FeedParser().parse(fetched(xml))
    assert feed.format is FeedFormat.ATOM
    assert feed.link == "https://example.com/"
    entry = feed.entries[0]
    assert entry.content == "<p>Content</p>"
    assert entry.author == "Jane Doe"
    assert entry.categories == ("Technology", "AI")
    assert entry.published_at == datetime(2026, 7, 21, 7, 0, tzinfo=timezone.utc)


def test_parse_preserves_bozo_warning_for_recoverable_feed():
    xml = b"<rss version='2.0'><channel><title>x</title></channel>"
    feed = FeedParser().parse(fetched(xml))
    assert feed.format is FeedFormat.RSS
    assert feed.warnings


def test_parse_rejects_empty_and_not_modified():
    parser = FeedParser()
    with pytest.raises(EmptyFeedError):
        parser.parse(fetched(None))
    with pytest.raises(EmptyFeedError):
        parser.parse(fetched(None, 304))


def test_parse_rejects_unsupported_document():
    with pytest.raises(UnsupportedFeedFormatError):
        FeedParser().parse(fetched(b"<html><body>not a feed</body></html>"))
