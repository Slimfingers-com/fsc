from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.enums.article_identity_type import ArticleIdentityType
from app.enums.article_pipeline import ArticlePipeline
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.article_processing import (
    ArticleProcessingRun,
    ArticleProcessingState,
)
from app.models.feed import Feed
from app.models.source import Source
from app.services.article_normalization import (
    ArticleNormalizationRunner,
    ArticleNormalizationService,
)
from tests.conftest import TestSessionLocal


def _create_article():
    token = uuid4().hex

    with TestSessionLocal.begin() as db:
        source = Source(
            name=token,
            normalized_name=token,
            slug=token,
            url=f"https://{token}.test",
            source_type=SourceType.NEWS,
        )

        feed = Feed(
            source=source,
            name="Main",
            url=f"https://{token}.test/feed",
        )

        article = Article(
            feed=feed,
            identity_type=ArticleIdentityType.DERIVED,
            identity_key=token.ljust(64, "0")[:64],
            title="<b>Title</b>",
            content=(
                "<p>This is a sufficiently long English "
                "article body for language detection.</p>"
            ),
        )

        db.add(article)
        db.flush()

        return article.id


def test_service_populates_normalized_fields():
    now = datetime(
        2026,
        7,
        21,
        12,
        0,
        tzinfo=UTC,
    )

    article = Article(
        identity_type=ArticleIdentityType.GUID,
        identity_key="a" * 64,
        title="<b>Title</b>",
        content=(
            "<p>This is a sufficiently long English "
            "article body for language detection.</p>"
        ),
    )

    service = ArticleNormalizationService(
        clock=lambda: now
    )

    changed = service.normalize_article(
        article
    )

    assert changed is True
    assert article.normalized_title == "Title"
    assert article.normalized_text.startswith("This is")
    assert article.language_code == "en"
    assert article.word_count > 0
    assert article.reading_time_minutes == 1
    assert article.normalization_version == 1
    assert article.normalized_at == now


def test_service_marks_equal_content_unchanged_but_refreshes_timestamp():
    first_time = datetime(
        2026,
        7,
        21,
        12,
        0,
        tzinfo=UTC,
    )
    second_time = datetime(
        2026,
        7,
        21,
        13,
        0,
        tzinfo=UTC,
    )

    article = Article(
        identity_type=ArticleIdentityType.GUID,
        identity_key="b" * 64,
        title="Title",
        summary="A short body",
    )

    ArticleNormalizationService(
        clock=lambda: first_time
    ).normalize_article(article)

    changed = ArticleNormalizationService(
        clock=lambda: second_time
    ).normalize_article(article)

    assert changed is False
    assert article.normalized_at == second_time


def test_candidate_changes_when_source_content_changes():
    article = Article(
        id=uuid4(),
        identity_type=ArticleIdentityType.GUID,
        identity_key="c" * 64,
        title="Title",
        content="First",
    )

    service = ArticleNormalizationService()

    first = service.candidate(article)

    article.content = "Second"

    second = service.candidate(article)

    assert first.input_hash != second.input_hash
    assert first.provider == "content_normalizer"
    assert first.provider_version == "1"
    assert first.configuration_version == "1"


def test_runner_normalizes_and_records_successful_processing():
    article_id = _create_article()

    runner = ArticleNormalizationRunner(
        TestSessionLocal,
        worker_id="normalizer-test",
    )

    result = runner.run_pending(
        limit=1
    )

    assert result.processed == 1
    assert result.changed == 1
    assert result.unchanged == 0

    with TestSessionLocal() as db:
        article = db.get(
            Article,
            article_id,
        )

        state = db.scalar(
            select(ArticleProcessingState).where(
                ArticleProcessingState.article_id
                == article_id,
                ArticleProcessingState.pipeline
                == ArticlePipeline.NORMALIZATION.value,
            )
        )

        run = db.scalar(
            select(ArticleProcessingRun).where(
                ArticleProcessingRun.article_id
                == article_id,
                ArticleProcessingRun.pipeline
                == ArticlePipeline.NORMALIZATION.value,
            )
        )

        assert article.normalized_at is not None
        assert article.normalized_text is not None

        assert state is not None
        assert state.processed_input_hash is not None
        assert state.claimed_by is None
        assert state.attempt_count == 1

        assert run is not None
        assert run.outcome == "succeeded"
        assert run.finished_at is not None


def test_runner_does_not_process_unchanged_article_twice():
    article_id = _create_article()

    runner = ArticleNormalizationRunner(
        TestSessionLocal,
        worker_id="normalizer-test",
    )

    first = runner.run_pending(
        limit=1
    )
    second = runner.run_pending(
        limit=1
    )

    assert first.processed == 1
    assert second.processed == 0

    with TestSessionLocal() as db:
        runs = list(
            db.scalars(
                select(ArticleProcessingRun).where(
                    ArticleProcessingRun.article_id
                    == article_id,
                    ArticleProcessingRun.pipeline
                    == ArticlePipeline.NORMALIZATION.value,
                )
            )
        )

        assert len(runs) == 1