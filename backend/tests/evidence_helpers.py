import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from app.analysis.provider import TextPart
from app.enums.article_identity_type import ArticleIdentityType
from app.enums.article_pipeline import ArticlePipeline
from app.enums.source_type import SourceType
from app.enums.story_pipeline import StoryPipeline
from app.models.article import Article
from app.models.article_processing import ArticleProcessingRun
from app.models.claim import ArticleClaim
from app.models.claim_relation import StoryClaimGroup, StoryClaimGroupMember
from app.models.feed import Feed
from app.models.perspective import ArticlePerspective
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.models.story_processing import StoryProcessingRun
from app.perspectives.provider import PerspectiveKind


def add_article_run(db, article, pipeline):
    now = datetime.now(UTC)
    run = ArticleProcessingRun(
        article_id=article.id,
        processing_state_id=None,
        pipeline=pipeline,
        input_hash=uuid4().hex * 2,
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


def build_evidence_story(
    db,
    *,
    specs=None,
):
    specs = specs or [
        {
            "source_type": SourceType.NEWS,
            "claim_text": "The climate plan begins Monday.",
            "quoted": False,
        },
        {
            "source_type": SourceType.PRIMARY_SOURCE,
            "claim_text": "The climate plan begins Monday.",
            "quoted": False,
        },
    ]

    story = Story(language_code="en")
    db.add(story)
    db.flush()

    claims = []
    sources = []
    articles = []

    for index, spec in enumerate(specs):
        slug = f"evidence-{index}-{uuid4().hex}"
        source = Source(
            name=slug,
            normalized_name=slug,
            slug=slug,
            url=f"https://{slug}.test",
            source_type=spec["source_type"],
        )
        feed = Feed(
            source=source,
            name="Main",
            url=f"https://{slug}.test/feed",
        )
        text = spec["claim_text"]
        article = Article(
            feed=feed,
            identity_type=ArticleIdentityType.DERIVED,
            identity_key=uuid4().hex * 2,
            title=spec.get("title") or f"Evidence {index}",
            normalized_title=(
                spec.get("title") or f"Evidence {index}"
            ).casefold(),
            normalized_text=text,
            language_code="en",
            content_hash=uuid4().hex * 2,
            normalization_version=1,
            normalized_at=datetime.now(UTC),
            published_at=datetime.now(UTC),
            link=f"https://{slug}.test/article",
        )
        db.add(article)
        db.flush()

        cluster_run = add_article_run(
            db,
            article,
            ArticlePipeline.STORY_CLUSTERING.value,
        )
        db.add(
            StoryArticle(
                story_id=story.id,
                article_id=article.id,
                processing_run_id=cluster_run.id,
                article_title=article.title,
                article_time=article.published_at,
                title_terms=[],
                entity_ids=[],
                topic_ids=[],
                similarity_score=0.0 if index == 0 else 0.9,
                match_kind="created" if index == 0 else "matched",
                match_details=None,
                clustered_at=datetime.now(UTC),
            )
        )

        claim_run = add_article_run(
            db,
            article,
            ArticlePipeline.CLAIM_EXTRACTION.value,
        )
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

        if spec.get("quoted"):
            perspective_run = add_article_run(
                db,
                article,
                ArticlePipeline.PERSPECTIVE_ANALYSIS.value,
            )
            db.add(
                ArticlePerspective(
                    article_id=article.id,
                    claim_id=claim.id,
                    processing_run_id=perspective_run.id,
                    holder_entity_id=None,
                    holder_text=None,
                    holder_start_offset=None,
                    holder_end_offset=None,
                    perspective_kind=PerspectiveKind.UNATTRIBUTED,
                    evidence_text=text,
                    text_source=TextPart.BODY,
                    start_offset=0,
                    end_offset=len(text),
                    sentence_index=0,
                    confidence=0.9,
                    analysis_provider="test",
                    analysis_version="1",
                    analyzed_at=datetime.now(UTC),
                )
            )
            # Use a quoted attribution only when a holder can be represented.
            # Tests that need the direct-quote signal update the perspective kind
            # with a dedicated valid fixture.

        claims.append(claim)
        sources.append(source)
        articles.append(article)

    relation_run = StoryProcessingRun(
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
    db.add(relation_run)
    db.flush()

    group = StoryClaimGroup(
        story_id=story.id,
        processing_run_id=relation_run.id,
        representative_claim_id=claims[0].id,
        group_hash=uuid4().hex * 2,
        confidence=0.9,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )
    db.add(group)
    db.flush()

    for claim in claims:
        db.add(
            StoryClaimGroupMember(
                group_id=group.id,
                claim_id=claim.id,
                processing_run_id=relation_run.id,
                similarity_score=1.0,
                match_kind="exact",
            )
        )
    db.flush()

    return {
        "story": story,
        "group": group,
        "claims": claims,
        "sources": sources,
        "articles": articles,
        "relation_run": relation_run,
    }
