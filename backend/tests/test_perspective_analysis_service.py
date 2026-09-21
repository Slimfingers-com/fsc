from datetime import UTC, datetime
import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.analysis.provider import EntityType, TextPart
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
from app.models.entity import ArticleEntity, Entity
from app.models.feed import Feed
from app.models.perspective import ArticlePerspective
from app.models.source import Source
from app.perspectives.provider import (
    PerspectiveAnalysisResult,
    PerspectiveAttribution,
    PerspectiveKind,
)
from app.services.perspective_analysis import (
    PerspectiveAnalysisService,
)


def create_inputs(db):
    text = (
        "Alice Smith said the climate plan will begin Monday."
    )
    source = Source(
        name="Perspective Source",
        normalized_name=(
            "perspective-source"
        ),
        slug="perspective-source",
        url="https://perspective.test",
        source_type=SourceType.NEWS,
    )
    feed = Feed(
        source=source,
        name="Main",
        url=(
            "https://perspective.test/feed"
        ),
    )
    article = Article(
        feed=feed,
        identity_type=(
            ArticleIdentityType.DERIVED
        ),
        identity_key="a" * 64,
        normalized_title="Update",
        normalized_text=text,
        language_code="en",
        content_hash="b" * 64,
        normalization_version=1,
        normalized_at=datetime.now(UTC),
    )
    db.add(article)
    db.flush()

    claim_run = ArticleProcessingRun(
        article_id=article.id,
        processing_state_id=None,
        pipeline=(
            ArticlePipeline
            .CLAIM_EXTRACTION
            .value
        ),
        input_hash="c" * 64,
        provider="test-claim",
        provider_version="1",
        configuration_version="1",
        worker_id="test",
        attempt_number=1,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        outcome="succeeded",
    )
    db.add(claim_run)
    db.flush()

    normalized = text.casefold()
    claim = ArticleClaim(
        article_id=article.id,
        processing_run_id=(
            claim_run.id
        ),
        claim_text=text,
        normalized_claim=normalized,
        claim_hash=hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest(),
        text_source=TextPart.BODY,
        start_offset=0,
        end_offset=len(text),
        sentence_index=0,
        confidence=0.9,
        extraction_provider=(
            "test-claim"
        ),
        extraction_version="1",
        extracted_at=datetime.now(UTC),
    )
    db.add(claim)

    entity = Entity(
        canonical_name="Alice Smith",
        normalized_name=(
            "alice smith"
        ),
        entity_type=EntityType.PERSON,
    )
    db.add(entity)
    db.flush()

    mention = ArticleEntity(
        article_id=article.id,
        entity_id=entity.id,
        processing_run_id=None,
        mention_text="Alice Smith",
        normalized_mention=(
            "alice smith"
        ),
        entity_type=EntityType.PERSON,
        text_source=TextPart.BODY,
        start_offset=0,
        end_offset=len(
            "Alice Smith"
        ),
        sentence_index=0,
        confidence=0.9,
        salience=0.8,
        extraction_provider=(
            "test-entity"
        ),
        extraction_version="1",
    )
    db.add(mention)
    db.flush()

    return (
        article,
        claim,
        mention,
    )


def create_perspective_run(
    db,
    article,
    claim,
    mention,
    service,
):
    candidate = service.candidate(
        article,
        claims=[claim],
        mentions=[mention],
    )
    run = ArticleProcessingRun(
        article_id=article.id,
        processing_state_id=None,
        pipeline=(
            ArticlePipeline
            .PERSPECTIVE_ANALYSIS
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
        started_at=datetime.now(UTC),
    )
    db.add(run)
    db.flush()
    return run


def test_processing_identity_tracks_claims_and_mentions(
    db,
):
    (
        article,
        claim,
        mention,
    ) = create_inputs(db)
    service = (
        PerspectiveAnalysisService()
    )

    first = service.candidate(
        article,
        claims=[claim],
        mentions=[mention],
    )

    mention.confidence = 0.81
    db.flush()

    second = service.candidate(
        article,
        claims=[claim],
        mentions=[mention],
    )

    assert (
        first.input_hash
        != second.input_hash
    )


def test_service_persists_and_soft_deletes_previous_generation(
    db,
):
    (
        article,
        claim,
        mention,
    ) = create_inputs(db)
    service = (
        PerspectiveAnalysisService()
    )
    prepared = service.prepare(
        article,
        claims=[claim],
        mentions=[mention],
    )
    result = service.run_provider(
        prepared
    )
    first_run = (
        create_perspective_run(
            db,
            article,
            claim,
            mention,
            service,
        )
    )

    service.persist_result(
        db,
        article,
        claims=[claim],
        mentions=[mention],
        prepared=prepared,
        result=result,
        processing_run_id=(
            first_run.id
        ),
        analyzed_at=(
            datetime.now(UTC)
        ),
    )

    first_id = db.scalar(
        select(
            ArticlePerspective.id
        ).where(
            ArticlePerspective.deleted_at
            .is_(None)
        )
    )
    assert first_id is not None

    first_run.finished_at = (
        datetime.now(UTC)
    )
    first_run.outcome = "succeeded"
    db.flush()

    second_run = (
        create_perspective_run(
            db,
            article,
            claim,
            mention,
            service,
        )
    )

    service.persist_result(
        db,
        article,
        claims=[claim],
        mentions=[mention],
        prepared=prepared,
        result=result,
        processing_run_id=(
            second_run.id
        ),
        analyzed_at=(
            datetime.now(UTC)
        ),
    )

    assert db.scalar(
        select(func.count())
        .select_from(
            ArticlePerspective
        )
        .where(
            ArticlePerspective.article_id
            == article.id
        )
    ) == 2
    active = db.scalar(
        select(
            ArticlePerspective
        ).where(
            ArticlePerspective.article_id
            == article.id,
            ArticlePerspective.deleted_at
            .is_(None),
        )
    )
    assert active is not None
    assert active.id != first_id
    assert (
        active.holder_entity_id
        == mention.entity_id
    )
    assert (
        active.perspective_kind
        == PerspectiveKind.REPORTED
    )


def test_invalid_provider_result_preserves_previous_generation(
    db,
):
    (
        article,
        claim,
        mention,
    ) = create_inputs(db)
    service = (
        PerspectiveAnalysisService()
    )
    prepared = service.prepare(
        article,
        claims=[claim],
        mentions=[mention],
    )
    valid = service.run_provider(
        prepared
    )
    first_run = (
        create_perspective_run(
            db,
            article,
            claim,
            mention,
            service,
        )
    )
    service.persist_result(
        db,
        article,
        claims=[claim],
        mentions=[mention],
        prepared=prepared,
        result=valid,
        processing_run_id=(
            first_run.id
        ),
        analyzed_at=(
            datetime.now(UTC)
        ),
    )
    first_run.finished_at = (
        datetime.now(UTC)
    )
    first_run.outcome = "succeeded"
    db.flush()

    active_id = db.scalar(
        select(
            ArticlePerspective.id
        ).where(
            ArticlePerspective.deleted_at
            .is_(None)
        )
    )
    second_run = (
        create_perspective_run(
            db,
            article,
            claim,
            mention,
            service,
        )
    )
    invalid = (
        PerspectiveAnalysisResult(
            attributions=(
                PerspectiveAttribution(
                    claim_id=claim.id,
                    perspective_kind=(
                        PerspectiveKind
                        .REPORTED
                    ),
                    holder_mention_id=(
                        uuid4()
                    ),
                    evidence_text=(
                        article.normalized_text
                    ),
                    text_source=(
                        TextPart.BODY
                    ),
                    start_offset=0,
                    end_offset=len(
                        article.normalized_text
                    ),
                    sentence_index=0,
                    confidence=0.9,
                ),
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="unknown holder",
    ):
        service.persist_result(
            db,
            article,
            claims=[claim],
            mentions=[mention],
            prepared=prepared,
            result=invalid,
            processing_run_id=(
                second_run.id
            ),
            analyzed_at=(
                datetime.now(UTC)
            ),
        )

    assert db.scalar(
        select(
            ArticlePerspective.id
        ).where(
            ArticlePerspective.deleted_at
            .is_(None)
        )
    ) == active_id


def test_stale_article_input_preserves_previous_generation(
    db,
):
    (
        article,
        claim,
        mention,
    ) = create_inputs(db)
    service = (
        PerspectiveAnalysisService()
    )
    prepared = service.prepare(
        article,
        claims=[claim],
        mentions=[mention],
    )
    result = service.run_provider(
        prepared
    )
    first_run = (
        create_perspective_run(
            db,
            article,
            claim,
            mention,
            service,
        )
    )
    service.persist_result(
        db,
        article,
        claims=[claim],
        mentions=[mention],
        prepared=prepared,
        result=result,
        processing_run_id=(
            first_run.id
        ),
        analyzed_at=(
            datetime.now(UTC)
        ),
    )

    active_id = db.scalar(
        select(
            ArticlePerspective.id
        ).where(
            ArticlePerspective.deleted_at
            .is_(None)
        )
    )

    first_run.finished_at = (
        datetime.now(UTC)
    )
    first_run.outcome = "succeeded"
    db.flush()
    second_run = (
        create_perspective_run(
            db,
            article,
            claim,
            mention,
            service,
        )
    )

    article.normalized_text = (
        "Changed normalized text that no longer contains the old claim."
    )
    article.content_hash = "d" * 64
    db.flush()

    with pytest.raises(
        ValueError,
        match="inputs changed",
    ):
        service.persist_result(
            db,
            article,
            claims=[claim],
            mentions=[mention],
            prepared=prepared,
            result=result,
            processing_run_id=(
                second_run.id
            ),
            analyzed_at=(
                datetime.now(UTC)
            ),
        )

    assert db.scalar(
        select(
            ArticlePerspective.id
        ).where(
            ArticlePerspective.deleted_at
            .is_(None)
        )
    ) == active_id
