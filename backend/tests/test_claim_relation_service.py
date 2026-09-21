from datetime import UTC, datetime
import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.analysis.provider import TextPart
from app.claim_relations.provider import (
    ClaimGroupMemberResult,
    ClaimGroupResult,
    ClaimGroupMatchKind,
    StoryClaimAnalysisResult,
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
from app.enums.story_pipeline import (
    StoryPipeline,
)
from app.models.article import Article
from app.models.article_processing import (
    ArticleProcessingRun,
)
from app.models.claim import ArticleClaim
from app.models.claim_relation import (
    StoryClaimGroup,
    StoryClaimRelation,
)
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.models.story_processing import (
    StoryProcessingRun,
)
from app.services.claim_relations import (
    ClaimRelationService,
)


def add_article_run(
    db,
    article,
    pipeline,
):
    now = datetime.now(UTC)
    run = ArticleProcessingRun(
        article_id=article.id,
        processing_state_id=None,
        pipeline=pipeline,
        input_hash=(
            uuid4().hex * 2
        ),
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
    return run


def create_story(
    db,
    texts,
):
    story = Story(
        language_code="en"
    )
    db.add(story)
    db.flush()

    claims = []

    for index, text in enumerate(texts):
        token = (
            f"relation-{uuid4().hex}"
        )
        source = Source(
            name=token,
            normalized_name=token,
            slug=token,
            url=(
                f"https://{token}.test"
            ),
            source_type=(
                SourceType.NEWS
            ),
        )
        feed = Feed(
            source=source,
            name="Main",
            url=(
                f"https://{token}.test/feed"
            ),
        )
        article = Article(
            feed=feed,
            identity_type=(
                ArticleIdentityType
                .DERIVED
            ),
            identity_key=(
                uuid4().hex * 2
            ),
            title=f"Article {index}",
            normalized_title=(
                f"Article {index}"
            ),
            normalized_text=text,
            language_code="en",
            content_hash=(
                uuid4().hex * 2
            ),
            normalization_version=1,
            normalized_at=(
                datetime.now(UTC)
            ),
            published_at=(
                datetime.now(UTC)
            ),
        )
        db.add(article)
        db.flush()

        clustering_run = (
            add_article_run(
                db,
                article,
                ArticlePipeline
                .STORY_CLUSTERING
                .value,
            )
        )
        db.add(
            StoryArticle(
                story_id=story.id,
                article_id=article.id,
                processing_run_id=(
                    clustering_run.id
                ),
                article_title=(
                    article.title
                ),
                article_time=(
                    article.published_at
                ),
                title_terms=[],
                entity_ids=[],
                topic_ids=[],
                similarity_score=(
                    0.0
                    if index == 0
                    else 0.9
                ),
                match_kind=(
                    "created"
                    if index == 0
                    else "matched"
                ),
                match_details=None,
                clustered_at=(
                    datetime.now(UTC)
                ),
            )
        )

        claim_run = add_article_run(
            db,
            article,
            ArticlePipeline
            .CLAIM_EXTRACTION
            .value,
        )
        normalized = (
            text.casefold().rstrip(".")
        )
        claim = ArticleClaim(
            article_id=article.id,
            processing_run_id=(
                claim_run.id
            ),
            claim_text=text,
            normalized_claim=normalized,
            claim_hash=hashlib.sha256(
                normalized.encode(
                    "utf-8"
                )
            ).hexdigest(),
            text_source=TextPart.BODY,
            start_offset=0,
            end_offset=len(text),
            sentence_index=0,
            confidence=0.9,
            extraction_provider="test",
            extraction_version="1",
            extracted_at=(
                datetime.now(UTC)
            ),
        )
        db.add(claim)
        claims.append(claim)

    db.flush()
    return story, claims


def add_story_run(
    db,
    snapshot,
    service,
):
    candidate = service.candidate(
        snapshot
    )
    run = StoryProcessingRun(
        story_id=(
            snapshot.story.id
        ),
        processing_state_id=None,
        pipeline=(
            StoryPipeline
            .CLAIM_RELATIONS
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
        started_at=(
            datetime.now(UTC)
        ),
    )
    db.add(run)
    db.flush()
    return run


def test_processing_identity_tracks_claim_generation(
    db,
):
    story, claims = create_story(
        db,
        [
            "The climate plan begins Monday.",
            "The climate plan begins Monday.",
        ],
    )
    service = (
        ClaimRelationService()
    )
    snapshot = (
        service.load_snapshot(
            db,
            story_id=story.id,
        )
    )
    assert snapshot is not None

    first = service.candidate(
        snapshot
    )

    claims[0].confidence = 0.81
    db.flush()

    changed = service.load_snapshot(
        db,
        story_id=story.id,
    )
    assert changed is not None
    second = service.candidate(
        changed
    )

    assert (
        first.input_hash
        != second.input_hash
    )


def test_service_replaces_active_generation_atomically(
    db,
):
    story, _ = create_story(
        db,
        [
            "The climate plan will begin Monday.",
            "The climate plan will not begin Monday.",
        ],
    )
    service = (
        ClaimRelationService()
    )
    snapshot = (
        service.load_snapshot(
            db,
            story_id=story.id,
        )
    )
    assert snapshot is not None
    prepared = service.prepare(
        snapshot
    )
    result = service.run_provider(
        prepared
    )
    first_run = add_story_run(
        db,
        snapshot,
        service,
    )

    service.persist_result(
        db,
        snapshot,
        prepared=prepared,
        result=result,
        processing_run_id=(
            first_run.id
        ),
        analyzed_at=(
            datetime.now(UTC)
        ),
    )

    assert db.scalar(
        select(func.count())
        .select_from(
            StoryClaimGroup
        )
        .where(
            StoryClaimGroup.story_id
            == story.id,
            StoryClaimGroup.deleted_at
            .is_(None),
        )
    ) == 2
    assert db.scalar(
        select(func.count())
        .select_from(
            StoryClaimRelation
        )
        .where(
            StoryClaimRelation.story_id
            == story.id,
            StoryClaimRelation.deleted_at
            .is_(None),
        )
    ) == 1

    first_run.finished_at = (
        datetime.now(UTC)
    )
    first_run.outcome = "succeeded"
    db.flush()

    second_run = add_story_run(
        db,
        snapshot,
        service,
    )
    service.persist_result(
        db,
        snapshot,
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
            StoryClaimGroup
        )
        .where(
            StoryClaimGroup.story_id
            == story.id
        )
    ) == 4
    assert db.scalar(
        select(func.count())
        .select_from(
            StoryClaimGroup
        )
        .where(
            StoryClaimGroup.story_id
            == story.id,
            StoryClaimGroup.deleted_at
            .is_(None),
        )
    ) == 2


def test_invalid_provider_partition_preserves_previous_generation(
    db,
):
    story, claims = create_story(
        db,
        [
            "The climate plan begins Monday.",
            "The climate plan begins Monday.",
        ],
    )
    service = (
        ClaimRelationService()
    )
    snapshot = (
        service.load_snapshot(
            db,
            story_id=story.id,
        )
    )
    assert snapshot is not None
    prepared = service.prepare(
        snapshot
    )
    valid = service.run_provider(
        prepared
    )
    first_run = add_story_run(
        db,
        snapshot,
        service,
    )
    service.persist_result(
        db,
        snapshot,
        prepared=prepared,
        result=valid,
        processing_run_id=(
            first_run.id
        ),
        analyzed_at=(
            datetime.now(UTC)
        ),
    )
    active_id = db.scalar(
        select(
            StoryClaimGroup.id
        ).where(
            StoryClaimGroup.story_id
            == story.id,
            StoryClaimGroup.deleted_at
            .is_(None),
        )
    )

    invalid = (
        StoryClaimAnalysisResult(
            groups=(
                ClaimGroupResult(
                    key="only-one",
                    representative_claim_id=(
                        claims[0].id
                    ),
                    members=(
                        ClaimGroupMemberResult(
                            claim_id=(
                                claims[0].id
                            ),
                            similarity_score=1.0,
                            match_kind=(
                                ClaimGroupMatchKind
                                .EXACT
                            ),
                        ),
                    ),
                    confidence=1.0,
                ),
            ),
            relations=(),
        )
    )

    first_run.finished_at = (
        datetime.now(UTC)
    )
    first_run.outcome = "succeeded"
    db.flush()
    second_run = add_story_run(
        db,
        snapshot,
        service,
    )

    with pytest.raises(
        ValueError,
        match="partition every input claim",
    ):
        service.persist_result(
            db,
            snapshot,
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
            StoryClaimGroup.id
        ).where(
            StoryClaimGroup.story_id
            == story.id,
            StoryClaimGroup.deleted_at
            .is_(None),
        )
    ) == active_id
