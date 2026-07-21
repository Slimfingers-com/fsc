from datetime import UTC, datetime

from app.enums.article_identity_type import ArticleIdentityType
from app.models.article import Article
from app.services.article_normalization import ArticleNormalizationService


def test_service_populates_normalized_fields():
    now = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
    article = Article(
        identity_type=ArticleIdentityType.GUID,
        identity_key="a" * 64,
        title="<b>Title</b>",
        content="<p>This is a sufficiently long English article body for language detection.</p>",
    )
    service = ArticleNormalizationService(clock=lambda: now)
    changed = service.normalize_article(article)
    assert changed is True
    assert article.normalized_title == "Title"
    assert article.normalized_text.startswith("This is")
    assert article.language_code == "en"
    assert article.word_count > 0
    assert article.reading_time_minutes == 1
    assert article.normalization_version == 1
    assert article.normalized_at == now


def test_service_marks_equal_content_unchanged_but_refreshes_timestamp():
    first_time = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
    second_time = datetime(2026, 7, 21, 13, 0, tzinfo=UTC)
    article = Article(
        identity_type=ArticleIdentityType.GUID,
        identity_key="b" * 64,
        title="Title",
        summary="A short body",
    )
    ArticleNormalizationService(clock=lambda: first_time).normalize_article(article)
    changed = ArticleNormalizationService(clock=lambda: second_time).normalize_article(article)
    assert changed is False
    assert article.normalized_at == second_time
