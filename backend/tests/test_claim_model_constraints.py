from datetime import UTC, datetime
import hashlib

import pytest
from sqlalchemy.exc import IntegrityError

from app.analysis.provider import TextPart
from app.enums.article_identity_type import (
    ArticleIdentityType,
)
from app.enums.article_pipeline import (
    ArticlePipeline,
)
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.article_processing import (
    ArticleProcessingRun,
)
from app.models.claim import ArticleClaim
from app.models.feed import Feed
from app.models.source import Source


def create_article_and_run(
    db,
    *,
    key: str,
):
    source = Source(
        name=f"Source {key}",
        normalized_name=f"source-{key}",
        slug=f"source-{key}",
        url=f"https://{key}.test",
        source_type=SourceType.NEWS,
    )
    feed = Feed(
        source=source,
        name="Main",
        url=f"https://{key}.test/feed",
    )
    article = Article(
        feed=feed,
        identity_type=(
            ArticleIdentityType.DERIVED
        ),
        identity_key=(key * 64)[:64],
        normalized_title="Update",
        normalized_text=(
            "The government approved the climate package."
        ),
        language_code="en",
        content_hash=(key * 64)[:64],
        normalization_version=1,
        normalized_at=datetime.now(UTC),
    )
    db.add(article)
    db.flush()

    now = datetime.now(UTC)
    run = ArticleProcessingRun(
        article_id=article.id,
        processing_state_id=None,
        pipeline=(
            ArticlePipeline
            .CLAIM_EXTRACTION
            .value
        ),
        input_hash=(key * 64)[:64],
        provider="test",
        provider_version="1",
        configuration_version="1",
        worker_id="test",
        attempt_number=1,
        started_at=now,
        finished_at=now,
        outcome="succeeded",
    )
    db.add(run)
    db.flush()
    return article, run


def make_claim(
    *,
    article,
    run,
    confidence: float = 0.9,
    start_offset: int = 0,
    end_offset: int = 44,
):
    text = (
        "The government approved the climate package."
    )
    normalized = text.casefold()
    return ArticleClaim(
        article_id=article.id,
        processing_run_id=run.id,
        claim_text=text,
        normalized_claim=normalized,
        claim_hash=hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest(),
        text_source=TextPart.BODY,
        start_offset=start_offset,
        end_offset=end_offset,
        sentence_index=0,
        confidence=confidence,
        extraction_provider="test",
        extraction_version="1",
        extracted_at=datetime.now(UTC),
    )


def assert_flush_fails(
    db,
    obj,
):
    savepoint = db.begin_nested()
    db.add(obj)
    try:
        with pytest.raises(
            IntegrityError
        ):
            db.flush()
    finally:
        if savepoint.is_active:
            savepoint.rollback()


def test_claim_constraints_reject_invalid_confidence_and_span(
    db,
):
    article, run = (
        create_article_and_run(
            db,
            key="a",
        )
    )

    assert_flush_fails(
        db,
        make_claim(
            article=article,
            run=run,
            confidence=1.1,
        ),
    )
    assert_flush_fails(
        db,
        make_claim(
            article=article,
            run=run,
            start_offset=5,
            end_offset=5,
        ),
    )


def test_only_one_active_claim_hash_per_article(
    db,
):
    article, first_run = (
        create_article_and_run(
            db,
            key="b",
        )
    )
    first = make_claim(
        article=article,
        run=first_run,
    )
    db.add(first)
    db.flush()

    now = datetime.now(UTC)
    second_run = ArticleProcessingRun(
        article_id=article.id,
        processing_state_id=None,
        pipeline=(
            ArticlePipeline
            .CLAIM_EXTRACTION
            .value
        ),
        input_hash="c" * 64,
        provider="test",
        provider_version="1",
        configuration_version="1",
        worker_id="test",
        attempt_number=2,
        started_at=now,
        finished_at=now,
        outcome="succeeded",
    )
    db.add(second_run)
    db.flush()

    duplicate = make_claim(
        article=article,
        run=second_run,
    )
    assert_flush_fails(
        db,
        duplicate,
    )

    first.deleted_at = (
        datetime.now(UTC)
    )
    db.flush()

    replacement = make_claim(
        article=article,
        run=second_run,
    )
    db.add(replacement)
    db.flush()

    assert replacement.id != first.id
