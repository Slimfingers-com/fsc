from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.analysis.provider import TextPart
from app.claims.provider import (
    ClaimExtractionResult,
    ClaimExtractor,
    ExtractedClaim,
)
from app.enums.article_identity_type import (
    ArticleIdentityType,
)
from app.enums.article_pipeline import (
    ArticlePipeline,
)
from app.enums.source_type import (
    SourceType,
)
from app.models.article import Article
from app.models.article_processing import (
    ArticleProcessingRun,
)
from app.models.claim import ArticleClaim
from app.models.feed import Feed
from app.models.source import Source
from app.services.claim_extraction import (
    ClaimExtractionService,
)


class FixedExtractor(ClaimExtractor):
    provider = "test-claims"
    version = "1"

    def __init__(
        self,
        text: str,
        *,
        confidence: float = 0.9,
    ) -> None:
        self.text = text
        self.confidence = confidence

    def extract(
        self,
        article,
    ):
        start = (
            article.normalized_text.index(
                self.text
            )
        )

        return ClaimExtractionResult(
            claims=(
                ExtractedClaim(
                    claim_text=self.text,
                    text_source=(
                        TextPart.BODY
                    ),
                    start_offset=start,
                    end_offset=(
                        start
                        + len(self.text)
                    ),
                    sentence_index=0,
                    confidence=(
                        self.confidence
                    ),
                ),
            )
        )


class InvalidExtractor(FixedExtractor):
    version = "invalid"

    def extract(
        self,
        article,
    ):
        return ClaimExtractionResult(
            claims=(
                ExtractedClaim(
                    claim_text=(
                        "does not match"
                    ),
                    text_source=(
                        TextPart.BODY
                    ),
                    start_offset=0,
                    end_offset=5,
                    sentence_index=0,
                    confidence=0.9,
                ),
            )
        )


def create_article(
    db,
):
    source = Source(
        name="Example",
        normalized_name="example",
        slug="example",
        url="https://example.test",
        source_type=(
            SourceType.NEWS
        ),
    )
    feed = Feed(
        source=source,
        name="Main",
        url=(
            "https://example.test/feed"
        ),
    )
    article = Article(
        feed=feed,
        identity_type=(
            ArticleIdentityType.DERIVED
        ),
        identity_key="c" * 64,
        normalized_title=(
            "Climate package approved"
        ),
        normalized_text=(
            "The government approved the climate package. "
            "The package costs 10 billion euros."
        ),
        language_code="en",
        content_hash="d" * 64,
        normalization_version=1,
        normalized_at=(
            datetime.now(UTC)
        ),
    )
    db.add(article)
    db.flush()
    return article


def create_run(
    db,
    article,
    *,
    service: ClaimExtractionService,
):
    now = datetime.now(UTC)
    candidate = service.candidate(
        article
    )
    run = ArticleProcessingRun(
        article_id=article.id,
        processing_state_id=None,
        pipeline=(
            ArticlePipeline
            .CLAIM_EXTRACTION
            .value
        ),
        input_hash=(
            candidate.input_hash
        ),
        provider=(
            candidate.provider
        ),
        provider_version=(
            candidate.provider_version
        ),
        configuration_version=(
            candidate.configuration_version
        ),
        worker_id="test",
        attempt_number=1,
        started_at=now,
    )
    db.add(run)
    db.flush()
    return run


def test_service_soft_deletes_previous_claim_generation(
    db,
):
    article = create_article(
        db
    )
    first_text = (
        "The government approved the climate package."
    )
    first_service = (
        ClaimExtractionService(
            extractor=(
                FixedExtractor(
                    first_text
                )
            )
        )
    )
    first_prepared = (
        first_service.prepare(
            article
        )
    )
    first_result = (
        first_service.run_provider(
            first_prepared
        )
    )
    first_run = create_run(
        db,
        article,
        service=first_service,
    )

    first_service.persist_result(
        db,
        article,
        prepared=first_prepared,
        result=first_result,
        processing_run_id=(
            first_run.id
        ),
        extracted_at=(
            datetime.now(UTC)
        ),
    )

    first_claim = db.scalar(
        select(ArticleClaim).where(
            ArticleClaim.article_id
            == article.id,
            ArticleClaim.deleted_at.is_(
                None
            ),
        )
    )

    assert first_claim is not None

    second_text = (
        "The package costs 10 billion euros."
    )
    second_service = (
        ClaimExtractionService(
            extractor=(
                FixedExtractor(
                    second_text
                )
            )
        )
    )
    second_prepared = (
        second_service.prepare(
            article
        )
    )
    second_result = (
        second_service.run_provider(
            second_prepared
        )
    )
    second_run = create_run(
        db,
        article,
        service=second_service,
    )

    second_service.persist_result(
        db,
        article,
        prepared=second_prepared,
        result=second_result,
        processing_run_id=(
            second_run.id
        ),
        extracted_at=(
            datetime.now(UTC)
        ),
    )

    assert db.scalar(
        select(func.count())
        .select_from(ArticleClaim)
        .where(
            ArticleClaim.article_id
            == article.id
        )
    ) == 2

    active = db.scalar(
        select(ArticleClaim).where(
            ArticleClaim.article_id
            == article.id,
            ArticleClaim.deleted_at.is_(
                None
            ),
        )
    )

    assert active is not None
    assert (
        active.claim_text
        == second_text
    )
    assert (
        first_claim.deleted_at
        is not None
    )


def test_invalid_provider_result_does_not_replace_previous_claims(
    db,
):
    article = create_article(
        db
    )
    text = (
        "The government approved the climate package."
    )
    service = (
        ClaimExtractionService(
            extractor=(
                FixedExtractor(
                    text
                )
            )
        )
    )
    prepared = service.prepare(
        article
    )
    run = create_run(
        db,
        article,
        service=service,
    )

    service.persist_result(
        db,
        article,
        prepared=prepared,
        result=(
            service.run_provider(
                prepared
            )
        ),
        processing_run_id=run.id,
        extracted_at=(
            datetime.now(UTC)
        ),
    )

    active_id = db.scalar(
        select(ArticleClaim.id).where(
            ArticleClaim.article_id
            == article.id,
            ArticleClaim.deleted_at.is_(
                None
            ),
        )
    )

    invalid = (
        ClaimExtractionService(
            extractor=(
                InvalidExtractor(
                    text
                )
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="offsets do not match",
    ):
        invalid.run_provider(
            invalid.prepare(
                article
            )
        )

    assert db.scalar(
        select(ArticleClaim.id).where(
            ArticleClaim.article_id
            == article.id,
            ArticleClaim.deleted_at.is_(
                None
            ),
        )
    ) == active_id


def test_service_rejects_stale_prepared_input_without_replacing_claims(
    db,
):
    article = create_article(
        db
    )
    text = (
        "The government approved the climate package."
    )
    service = ClaimExtractionService(
        extractor=FixedExtractor(
            text
        )
    )
    prepared = service.prepare(
        article
    )
    run = create_run(
        db,
        article,
        service=service,
    )
    result = service.run_provider(
        prepared
    )

    article.normalized_title = (
        "Changed title"
    )
    article.content_hash = "f" * 64
    db.flush()

    with pytest.raises(
        ValueError,
        match=(
            "article identity changed"
        ),
    ):
        service.persist_result(
            db,
            article,
            prepared=prepared,
            result=result,
            processing_run_id=(
                run.id
            ),
            extracted_at=(
                datetime.now(UTC)
            ),
        )

    assert db.scalar(
        select(func.count())
        .select_from(ArticleClaim)
        .where(
            ArticleClaim.article_id
            == article.id,
            ArticleClaim.deleted_at.is_(
                None
            ),
        )
    ) == 0


def test_service_rejects_mismatched_processing_run_without_replacing_claims(
    db,
):
    article = create_article(
        db
    )
    text = (
        "The government approved the climate package."
    )
    service = ClaimExtractionService(
        extractor=FixedExtractor(
            text
        )
    )
    prepared = service.prepare(
        article
    )
    valid_run = create_run(
        db,
        article,
        service=service,
    )
    result = service.run_provider(
        prepared
    )
    service.persist_result(
        db,
        article,
        prepared=prepared,
        result=result,
        processing_run_id=(
            valid_run.id
        ),
        extracted_at=(
            datetime.now(UTC)
        ),
    )
    active_id = db.scalar(
        select(ArticleClaim.id).where(
            ArticleClaim.article_id
            == article.id,
            ArticleClaim.deleted_at.is_(
                None
            ),
        )
    )

    other_article = Article(
        feed_id=article.feed_id,
        identity_type=(
            ArticleIdentityType.DERIVED
        ),
        identity_key="e" * 64,
        normalized_title=(
            article.normalized_title
        ),
        normalized_text=(
            article.normalized_text
        ),
        language_code=(
            article.language_code
        ),
        content_hash="e" * 64,
        normalization_version=1,
        normalized_at=(
            datetime.now(UTC)
        ),
    )
    db.add(other_article)
    db.flush()
    wrong_run = create_run(
        db,
        other_article,
        service=service,
    )

    with pytest.raises(
        ValueError,
        match=(
            "processing run does not match"
        ),
    ):
        service.persist_result(
            db,
            article,
            prepared=prepared,
            result=result,
            processing_run_id=(
                wrong_run.id
            ),
            extracted_at=(
                datetime.now(UTC)
            ),
        )

    assert db.scalar(
        select(ArticleClaim.id).where(
            ArticleClaim.article_id
            == article.id,
            ArticleClaim.deleted_at.is_(
                None
            ),
        )
    ) == active_id


def test_service_filters_low_confidence_claims(
    db,
):
    article = create_article(
        db
    )
    text = (
        "The government approved the climate package."
    )
    service = ClaimExtractionService(
        extractor=FixedExtractor(
            text,
            confidence=0.4,
        ),
        min_confidence=0.6,
    )
    prepared = service.prepare(
        article
    )
    run = create_run(
        db,
        article,
        service=service,
    )

    service.persist_result(
        db,
        article,
        prepared=prepared,
        result=(
            service.run_provider(
                prepared
            )
        ),
        processing_run_id=run.id,
        extracted_at=(
            datetime.now(UTC)
        ),
    )

    assert db.scalar(
        select(func.count())
        .select_from(ArticleClaim)
        .where(
            ArticleClaim.deleted_at.is_(
                None
            )
        )
    ) == 0
