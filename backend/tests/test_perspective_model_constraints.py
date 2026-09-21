from datetime import UTC, datetime
import hashlib
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

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
from app.models.entity import Entity
from app.models.feed import Feed
from app.models.perspective import ArticlePerspective
from app.models.source import Source
from app.perspectives.provider import PerspectiveKind


def create_bundle(
    db,
):
    token = uuid4().hex
    text = (
        "Alice Smith said the climate plan will begin Monday."
    )
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
        identity_type=(
            ArticleIdentityType.DERIVED
        ),
        identity_key=(
            uuid4().hex * 2
        ),
        normalized_title="Update",
        normalized_text=text,
        language_code="en",
        content_hash=(
            uuid4().hex * 2
        ),
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
        input_hash=(
            uuid4().hex * 2
        ),
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
    entity = Entity(
        canonical_name="Alice Smith",
        normalized_name=(
            f"alice-{token}"
        ),
        entity_type=EntityType.PERSON,
    )
    db.add_all(
        [
            claim,
            entity,
        ]
    )
    db.flush()

    return (
        article,
        claim,
        entity,
        text,
    )


def create_run(
    db,
    article,
):
    run = ArticleProcessingRun(
        article_id=article.id,
        processing_state_id=None,
        pipeline=(
            ArticlePipeline
            .PERSPECTIVE_ANALYSIS
            .value
        ),
        input_hash=(
            uuid4().hex * 2
        ),
        provider="test",
        provider_version="1",
        configuration_version="1",
        worker_id="test",
        attempt_number=1,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        outcome="succeeded",
    )
    db.add(run)
    db.flush()
    return run


def make_perspective(
    *,
    article,
    claim,
    entity,
    run,
    text,
    confidence: float = 0.9,
    start_offset: int = 0,
    end_offset: int | None = None,
    kind: PerspectiveKind = (
        PerspectiveKind.REPORTED
    ),
    holder: bool = True,
):
    return ArticlePerspective(
        article_id=article.id,
        claim_id=claim.id,
        processing_run_id=run.id,
        holder_entity_id=(
            entity.id
            if holder
            else None
        ),
        holder_text=(
            "Alice Smith"
            if holder
            else None
        ),
        holder_start_offset=(
            0
            if holder
            else None
        ),
        holder_end_offset=(
            len("Alice Smith")
            if holder
            else None
        ),
        perspective_kind=kind,
        evidence_text=text,
        text_source=TextPart.BODY,
        start_offset=start_offset,
        end_offset=(
            len(text)
            if end_offset is None
            else end_offset
        ),
        sentence_index=0,
        confidence=confidence,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )


def assert_flush_fails(
    db,
    obj,
):
    with pytest.raises(
        IntegrityError
    ):
        with db.begin_nested():
            db.add(obj)
            db.flush()


def test_perspective_constraints_reject_invalid_values(
    db,
):
    (
        article,
        claim,
        entity,
        text,
    ) = create_bundle(db)
    run = create_run(
        db,
        article,
    )

    assert_flush_fails(
        db,
        make_perspective(
            article=article,
            claim=claim,
            entity=entity,
            run=run,
            text=text,
            confidence=1.1,
        ),
    )
    assert_flush_fails(
        db,
        make_perspective(
            article=article,
            claim=claim,
            entity=entity,
            run=run,
            text=text,
            start_offset=5,
            end_offset=5,
        ),
    )
    assert_flush_fails(
        db,
        make_perspective(
            article=article,
            claim=claim,
            entity=entity,
            run=run,
            text=text,
            kind=(
                PerspectiveKind
                .UNATTRIBUTED
            ),
            holder=True,
        ),
    )


def test_only_one_active_attribution_per_claim_holder_kind(
    db,
):
    (
        article,
        claim,
        entity,
        text,
    ) = create_bundle(db)
    first_run = create_run(
        db,
        article,
    )
    first = make_perspective(
        article=article,
        claim=claim,
        entity=entity,
        run=first_run,
        text=text,
    )
    db.add(first)
    db.flush()

    second_run = create_run(
        db,
        article,
    )
    duplicate = make_perspective(
        article=article,
        claim=claim,
        entity=entity,
        run=second_run,
        text=text,
    )
    assert_flush_fails(
        db,
        duplicate,
    )

    first.deleted_at = (
        datetime.now(UTC)
    )
    db.flush()

    replacement = make_perspective(
        article=article,
        claim=claim,
        entity=entity,
        run=second_run,
        text=text,
    )
    db.add(replacement)
    db.flush()

    assert replacement.id != first.id


def test_only_one_active_unattributed_row_per_claim(
    db,
):
    (
        article,
        claim,
        entity,
        text,
    ) = create_bundle(db)
    first_run = create_run(
        db,
        article,
    )
    first = make_perspective(
        article=article,
        claim=claim,
        entity=entity,
        run=first_run,
        text=text,
        kind=(
            PerspectiveKind
            .UNATTRIBUTED
        ),
        holder=False,
    )
    db.add(first)
    db.flush()

    second_run = create_run(
        db,
        article,
    )
    duplicate = make_perspective(
        article=article,
        claim=claim,
        entity=entity,
        run=second_run,
        text=text,
        kind=(
            PerspectiveKind
            .UNATTRIBUTED
        ),
        holder=False,
    )
    assert_flush_fails(
        db,
        duplicate,
    )
