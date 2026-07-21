from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from app.enums.article_identity_type import ArticleIdentityType
from app.ingestion.models import ParsedFeedEntry


@dataclass(frozen=True, slots=True)
class ArticleIdentity:
    identity_type: ArticleIdentityType
    identity_key: str


def build_article_identity(entry: ParsedFeedEntry) -> ArticleIdentity:
    guid = _clean(entry.external_id)
    if guid:
        return _build(ArticleIdentityType.GUID, guid)

    link = _clean(entry.link)
    if link:
        return _build(ArticleIdentityType.LINK, link)

    derived_value = "\x1f".join(
        (
            _clean(entry.title) or "",
            _datetime_value(entry.published_at),
            _clean(entry.author) or "",
        )
    )
    return _build(ArticleIdentityType.DERIVED, derived_value)


def _build(
    identity_type: ArticleIdentityType,
    value: str,
) -> ArticleIdentity:
    payload = f"{identity_type.value}\x00{value}".encode("utf-8")
    return ArticleIdentity(
        identity_type=identity_type,
        identity_key=sha256(payload).hexdigest(),
    )


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _datetime_value(value: datetime | None) -> str:
    return value.isoformat() if value else ""
