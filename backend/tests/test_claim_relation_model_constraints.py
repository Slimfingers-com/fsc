from datetime import UTC, datetime
import hashlib
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.analysis.provider import TextPart
from app.claim_relations.provider import (
    ClaimGroupMatchKind,
    ClaimRelationKind,
)
from app.enums.article_identity_type import ArticleIdentityType
from app.enums.article_pipeline import ArticlePipeline
from app.enums.source_type import SourceType
from app.enums.story_pipeline import StoryPipeline
from app.models.article import Article
from app.models.article_processing import ArticleProcessingRun
from app.models.claim import ArticleClaim
from app.models.claim_relation import (
    StoryClaimGroup,
    StoryClaimGroupMember,
    StoryClaimRelation,
)
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story
from app.models.story_processing import StoryProcessingRun


def assert_flush_fails(db, obj):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(obj)
            db.flush()


def create_bundle(db):
    token = uuid4().hex
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
    text = "The climate plan will begin Monday."
    article = Article(
        feed=feed,
        identity_type=ArticleIdentityType.DERIVED,
        identity_key=uuid4().hex * 2,
        normalized_title="Update",
        normalized_text=text,
        language_code="en",
        content_hash=uuid4().hex * 2,
        normalization_version=1,
        normalized_at=datetime.now(UTC),
    )
    story = Story(language_code="en")
    db.add_all([article, story])
    db.flush()

    claim_run = ArticleProcessingRun(
        article_id=article.id,
        processing_state_id=None,
        pipeline=ArticlePipeline.CLAIM_EXTRACTION.value,
        input_hash=uuid4().hex * 2,
        provider="test",
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

    normalized = text.casefold().rstrip(".")
    claim = ArticleClaim(
        article_id=article.id,
        processing_run_id=claim_run.id,
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
        extraction_provider="test",
        extraction_version="1",
        extracted_at=datetime.now(UTC),
    )
    db.add(claim)
    db.flush()

    run = StoryProcessingRun(
        story_id=story.id,
        processing_state_id=None,
        pipeline=StoryPipeline.CLAIM_RELATIONS.value,
        input_hash=uuid4().hex * 2,
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

    group = StoryClaimGroup(
        story_id=story.id,
        processing_run_id=run.id,
        representative_claim_id=claim.id,
        group_hash="a" * 64,
        confidence=0.9,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )
    db.add(group)
    db.flush()

    return story, claim, run, group


def test_group_and_member_constraints(db):
    story, claim, run, group = create_bundle(db)

    invalid_group = StoryClaimGroup(
        story_id=story.id,
        processing_run_id=run.id,
        representative_claim_id=claim.id,
        group_hash="b" * 64,
        confidence=1.1,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )
    assert_flush_fails(db, invalid_group)

    invalid_member = StoryClaimGroupMember(
        group_id=group.id,
        claim_id=claim.id,
        processing_run_id=run.id,
        similarity_score=1.1,
        match_kind=ClaimGroupMatchKind.EXACT,
    )
    assert_flush_fails(db, invalid_member)


def test_only_one_active_group_hash_per_story(db):
    story, claim, run, first = create_bundle(db)

    second_run = StoryProcessingRun(
        story_id=story.id,
        processing_state_id=None,
        pipeline=StoryPipeline.CLAIM_RELATIONS.value,
        input_hash=uuid4().hex * 2,
        provider="test",
        provider_version="1",
        configuration_version="1",
        worker_id="test",
        attempt_number=2,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        outcome="succeeded",
    )
    db.add(second_run)
    db.flush()

    duplicate = StoryClaimGroup(
        story_id=story.id,
        processing_run_id=second_run.id,
        representative_claim_id=claim.id,
        group_hash=first.group_hash,
        confidence=0.9,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )
    assert_flush_fails(db, duplicate)

    first.deleted_at = datetime.now(UTC)
    db.flush()

    replacement = StoryClaimGroup(
        story_id=story.id,
        processing_run_id=second_run.id,
        representative_claim_id=claim.id,
        group_hash=first.group_hash,
        confidence=0.9,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )
    db.add(replacement)
    db.flush()
    assert replacement.id != first.id


def test_relation_rejects_same_group_and_invalid_confidence(db):
    story, _, run, group = create_bundle(db)

    same_group = StoryClaimRelation(
        story_id=story.id,
        processing_run_id=run.id,
        left_group_id=group.id,
        right_group_id=group.id,
        relation_kind=ClaimRelationKind.CONTRADICTS,
        confidence=0.9,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )
    assert_flush_fails(db, same_group)

    invalid_confidence = StoryClaimRelation(
        story_id=story.id,
        processing_run_id=run.id,
        left_group_id=group.id,
        right_group_id=uuid4(),
        relation_kind=ClaimRelationKind.CONTRADICTS,
        confidence=1.1,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )
    assert_flush_fails(db, invalid_confidence)
