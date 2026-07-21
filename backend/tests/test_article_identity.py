from datetime import UTC, datetime

from app.core.article_identity import build_article_identity
from app.enums.article_identity_type import ArticleIdentityType
from app.ingestion.models import ParsedFeedEntry


def entry(**overrides):
    values = {
        "external_id": None,
        "title": "Title",
        "link": None,
        "summary": None,
        "content": None,
        "author": "Author",
        "published_at": datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
        "updated_at": None,
        "categories": (),
        "enclosures": (),
    }
    values.update(overrides)
    return ParsedFeedEntry(**values)


def test_identity_prefers_guid_over_link():
    identity = build_article_identity(
        entry(external_id=" guid-1 ", link="https://example.com/1")
    )
    assert identity.identity_type is ArticleIdentityType.GUID
    assert len(identity.identity_key) == 64


def test_identity_uses_link_without_guid():
    identity = build_article_identity(entry(link="https://example.com/1"))
    assert identity.identity_type is ArticleIdentityType.LINK


def test_identity_is_deterministic_for_derived_values():
    first = build_article_identity(entry())
    second = build_article_identity(entry())
    assert first.identity_type is ArticleIdentityType.DERIVED
    assert first.identity_key == second.identity_key


def test_identity_type_is_part_of_hash_input():
    guid = build_article_identity(entry(external_id="same"))
    link = build_article_identity(entry(link="same"))
    assert guid.identity_key != link.identity_key
