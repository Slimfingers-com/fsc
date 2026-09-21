from datetime import UTC, datetime
import hashlib
from uuid import uuid4

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
from app.models.story import Story, StoryArticle
from app.models.story_processing import StoryProcessingRun


def add_article_run(db, article, pipeline: str):
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


def add_article_with_claim(
    db,
    *,
    story,
    slug: str,
    text: str,
    match_kind: str,
):
    source = Source(
        name=slug.title(),
        normalized_name=slug,
        slug=slug,
        url=f"https://{slug}.test",
        source_type=SourceType.NEWS,
    )
    feed = Feed(
        source=source,
        name="Main",
        url=f"https://{slug}.test/feed",
    )
    article = Article(
        feed=feed,
        identity_type=ArticleIdentityType.DERIVED,
        identity_key=uuid4().hex * 2,
        title=f"{slug} title",
        normalized_title=f"{slug} title",
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

    clustering_run = add_article_run(
        db,
        article,
        ArticlePipeline.STORY_CLUSTERING.value,
    )
    db.add(
        StoryArticle(
            story_id=story.id,
            article_id=article.id,
            processing_run_id=clustering_run.id,
            article_title=article.title,
            article_time=article.published_at,
            title_terms=[],
            entity_ids=[],
            topic_ids=[],
            similarity_score=0.0 if match_kind == "created" else 0.9,
            match_kind=match_kind,
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
    return source, article, claim


def add_story_run(db, story):
    now = datetime.now(UTC)
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
        started_at=now,
        finished_at=now,
        outcome="succeeded",
    )
    db.add(run)
    db.flush()
    return run


def add_group(
    db,
    *,
    story,
    run,
    representative,
    members,
    group_hash: str,
):
    group = StoryClaimGroup(
        story_id=story.id,
        processing_run_id=run.id,
        representative_claim_id=representative.id,
        group_hash=group_hash,
        confidence=0.9,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )
    db.add(group)
    db.flush()

    for claim in members:
        db.add(
            StoryClaimGroupMember(
                group_id=group.id,
                claim_id=claim.id,
                processing_run_id=run.id,
                similarity_score=1.0,
                match_kind=ClaimGroupMatchKind.EXACT,
            )
        )
    db.flush()
    return group


def build_story_results(db):
    story = Story(language_code="en")
    db.add(story)
    db.flush()

    alpha_source, _, alpha_claim = add_article_with_claim(
        db,
        story=story,
        slug=f"alpha-{uuid4().hex}",
        text="The climate plan will begin Monday.",
        match_kind="created",
    )
    beta_source, _, beta_claim = add_article_with_claim(
        db,
        story=story,
        slug=f"beta-{uuid4().hex}",
        text="The climate plan will begin Monday.",
        match_kind="matched",
    )
    gamma_source, gamma_article, gamma_claim = add_article_with_claim(
        db,
        story=story,
        slug=f"gamma-{uuid4().hex}",
        text="The climate plan will not begin Monday.",
        match_kind="matched",
    )

    run = add_story_run(db, story)
    positive = add_group(
        db,
        story=story,
        run=run,
        representative=alpha_claim,
        members=[alpha_claim, beta_claim],
        group_hash="a" * 64,
    )
    negative = add_group(
        db,
        story=story,
        run=run,
        representative=gamma_claim,
        members=[gamma_claim],
        group_hash="b" * 64,
    )
    relation = StoryClaimRelation(
        story_id=story.id,
        processing_run_id=run.id,
        left_group_id=positive.id,
        right_group_id=negative.id,
        relation_kind=ClaimRelationKind.CONTRADICTS,
        confidence=0.95,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )
    db.add(relation)
    db.flush()

    return {
        "story": story,
        "positive": positive,
        "negative": negative,
        "relation": relation,
        "alpha_source": alpha_source,
        "beta_source": beta_source,
        "gamma_source": gamma_source,
        "gamma_article": gamma_article,
        "gamma_claim": gamma_claim,
    }


def test_claim_group_and_relation_read_endpoints(client, db):
    data = build_story_results(db)
    story = data["story"]

    groups = client.get(
        f"/stories/{story.id}/claim-groups"
    )
    assert groups.status_code == 200
    payload = groups.json()
    assert payload["total"] == 2
    assert payload["items"][0]["source_count"] == 2
    assert payload["items"][0]["claim_count"] == 2

    filtered = client.get(
        f"/stories/{story.id}/claim-groups",
        params={"min_sources": 2},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert (
        filtered.json()["items"][0]["id"]
        == str(data["positive"].id)
    )

    detail = client.get(
        f"/claim-groups/{data['positive'].id}"
    )
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["claim_count"] == 2
    assert len(detail_payload["members"]) == 2
    assert {
        item["source_id"]
        for item in detail_payload["members"]
    } == {
        str(data["alpha_source"].id),
        str(data["beta_source"].id),
    }

    relations = client.get(
        f"/stories/{story.id}/claim-relations",
        params={
            "relation_kind": "contradicts",
            "min_confidence": 0.9,
        },
    )
    assert relations.status_code == 200
    relation_payload = relations.json()
    assert relation_payload["total"] == 1
    assert (
        relation_payload["items"][0]["id"]
        == str(data["relation"].id)
    )


def test_claim_relation_reads_hide_ineligible_representative(client, db):
    data = build_story_results(db)
    story = data["story"]

    data["gamma_source"].active = False
    db.flush()

    groups = client.get(
        f"/stories/{story.id}/claim-groups"
    )
    assert groups.status_code == 200
    assert groups.json()["total"] == 1

    detail = client.get(
        f"/claim-groups/{data['negative'].id}"
    )
    assert detail.status_code == 404

    relations = client.get(
        f"/stories/{story.id}/claim-relations"
    )
    assert relations.status_code == 200
    assert relations.json()["total"] == 0


def test_missing_story_and_group_return_404(client):
    missing = uuid4()

    assert client.get(
        f"/stories/{missing}/claim-groups"
    ).status_code == 404
    assert client.get(
        f"/stories/{missing}/claim-relations"
    ).status_code == 404
    assert client.get(
        f"/claim-groups/{missing}"
    ).status_code == 404
