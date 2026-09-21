from datetime import UTC, datetime
import hashlib
from uuid import uuid4

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
from app.models.story import Story, StoryArticle
from app.perspectives.provider import PerspectiveKind


def add_source(
    db,
    *,
    slug: str,
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
    db.add(source)
    db.flush()
    return source, feed


def add_article(
    db,
    *,
    feed,
    text: str,
):
    now = datetime.now(UTC)
    article = Article(
        feed=feed,
        identity_type=(
            ArticleIdentityType.DERIVED
        ),
        identity_key=(
            uuid4().hex * 2
        ),
        title="Current title",
        normalized_title=(
            "Current title"
        ),
        normalized_text=text,
        language_code="en",
        content_hash=(
            uuid4().hex * 2
        ),
        normalization_version=1,
        normalized_at=now,
        published_at=now,
        link=(
            f"https://{feed.source.slug}.test/article"
        ),
    )
    db.add(article)
    db.flush()
    return article


def add_run(
    db,
    *,
    article,
    pipeline: str,
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


def add_claim(
    db,
    *,
    article,
    text: str,
):
    run = add_run(
        db,
        article=article,
        pipeline=(
            ArticlePipeline
            .CLAIM_EXTRACTION
            .value
        ),
    )
    normalized = text.casefold()
    claim = ArticleClaim(
        article_id=article.id,
        processing_run_id=run.id,
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
    return claim


def add_entity(
    db,
    *,
    name: str,
):
    entity = Entity(
        canonical_name=name,
        normalized_name=(
            f"{name.casefold()}-{uuid4().hex}"
        ),
        entity_type=EntityType.PERSON,
    )
    db.add(entity)
    db.flush()
    return entity


def add_perspective(
    db,
    *,
    article,
    claim,
    text: str,
    entity=None,
    kind: PerspectiveKind = (
        PerspectiveKind.REPORTED
    ),
    confidence: float = 0.9,
):
    run = add_run(
        db,
        article=article,
        pipeline=(
            ArticlePipeline
            .PERSPECTIVE_ANALYSIS
            .value
        ),
    )
    item = ArticlePerspective(
        article_id=article.id,
        claim_id=claim.id,
        processing_run_id=run.id,
        holder_entity_id=(
            entity.id
            if entity is not None
            else None
        ),
        holder_text=(
            entity.canonical_name
            if entity is not None
            else None
        ),
        holder_start_offset=(
            0
            if entity is not None
            else None
        ),
        holder_end_offset=(
            len(
                entity.canonical_name
            )
            if entity is not None
            else None
        ),
        perspective_kind=kind,
        evidence_text=text,
        text_source=TextPart.BODY,
        start_offset=0,
        end_offset=len(text),
        sentence_index=0,
        confidence=confidence,
        analysis_provider="test",
        analysis_version="1",
        analyzed_at=datetime.now(UTC),
    )
    db.add(item)
    db.flush()
    return item


def add_story_membership(
    db,
    *,
    story=None,
    article,
):
    if story is None:
        story = Story(
            language_code="en"
        )
        db.add(story)
        db.flush()

    run = add_run(
        db,
        article=article,
        pipeline=(
            ArticlePipeline
            .STORY_CLUSTERING
            .value
        ),
    )
    membership = StoryArticle(
        story_id=story.id,
        article_id=article.id,
        processing_run_id=run.id,
        article_title=article.title,
        article_time=article.published_at,
        title_terms=[],
        entity_ids=[],
        topic_ids=[],
        similarity_score=0.0,
        match_kind="created",
        match_details=None,
        clustered_at=datetime.now(UTC),
    )
    db.add(membership)
    db.flush()
    return story


def test_perspective_read_endpoints(
    client,
    db,
):
    source, feed = add_source(
        db,
        slug="perspective-alpha",
    )
    text = (
        "Alice Smith said the climate plan will begin Monday."
    )
    article = add_article(
        db,
        feed=feed,
        text=text,
    )
    claim = add_claim(
        db,
        article=article,
        text=text,
    )
    entity = add_entity(
        db,
        name="Alice Smith",
    )
    perspective = add_perspective(
        db,
        article=article,
        claim=claim,
        text=text,
        entity=entity,
    )
    story = add_story_membership(
        db,
        article=article,
    )

    article_response = client.get(
        f"/articles/{article.id}/perspectives"
    )
    assert article_response.status_code == 200
    assert [
        item["id"]
        for item
        in article_response.json()
    ] == [
        str(perspective.id)
    ]

    claim_response = client.get(
        f"/claims/{claim.id}/perspectives"
    )
    assert claim_response.status_code == 200
    claim_data = (
        claim_response.json()[0]
    )
    assert (
        claim_data[
            "holder_entity_id"
        ]
        == str(entity.id)
    )
    assert (
        claim_data[
            "perspective_kind"
        ]
        == "reported"
    )

    story_response = client.get(
        f"/stories/{story.id}/perspectives"
    )
    assert story_response.status_code == 200
    data = story_response.json()
    assert data["total"] == 1
    assert (
        data["items"][0]["id"]
        == str(perspective.id)
    )
    assert (
        data["items"][0][
            "source_id"
        ]
        == str(source.id)
    )
    assert (
        data["items"][0][
            "claim_text"
        ]
        == text
    )


def test_perspective_reads_hide_deleted_claims_and_ineligible_sources(
    client,
    db,
):
    source, feed = add_source(
        db,
        slug="perspective-beta",
    )
    text = (
        "Alice Smith said the climate plan will begin Monday."
    )
    article = add_article(
        db,
        feed=feed,
        text=text,
    )
    claim = add_claim(
        db,
        article=article,
        text=text,
    )
    entity = add_entity(
        db,
        name="Alice Smith",
    )
    perspective = add_perspective(
        db,
        article=article,
        claim=claim,
        text=text,
        entity=entity,
    )
    story = add_story_membership(
        db,
        article=article,
    )

    perspective.deleted_at = (
        datetime.now(UTC)
    )
    db.flush()

    assert client.get(
        f"/articles/{article.id}/perspectives"
    ).json() == []
    assert client.get(
        f"/claims/{claim.id}/perspectives"
    ).json() == []
    assert client.get(
        f"/stories/{story.id}/perspectives"
    ).json()["total"] == 0

    perspective.deleted_at = None
    claim.deleted_at = datetime.now(UTC)
    db.flush()

    assert client.get(
        f"/articles/{article.id}/perspectives"
    ).json() == []
    assert client.get(
        f"/claims/{claim.id}/perspectives"
    ).status_code == 404
    assert client.get(
        f"/stories/{story.id}/perspectives"
    ).json()["total"] == 0

    claim.deleted_at = None
    source.active = False
    db.flush()

    assert client.get(
        f"/articles/{article.id}/perspectives"
    ).status_code == 404
    assert client.get(
        f"/claims/{claim.id}/perspectives"
    ).status_code == 404
    assert client.get(
        f"/stories/{story.id}/perspectives"
    ).status_code == 404


def test_story_perspective_filters_and_pagination(
    client,
    db,
):
    alpha, alpha_feed = add_source(
        db,
        slug="perspective-filter-a",
    )
    _, beta_feed = add_source(
        db,
        slug="perspective-filter-b",
    )

    first_text = (
        "Alice Smith said the climate plan will begin Monday."
    )
    second_text = (
        "The climate plan will begin Tuesday."
    )
    first = add_article(
        db,
        feed=alpha_feed,
        text=first_text,
    )
    second = add_article(
        db,
        feed=beta_feed,
        text=second_text,
    )

    story = add_story_membership(
        db,
        article=first,
    )
    add_story_membership(
        db,
        story=story,
        article=second,
    )

    entity = add_entity(
        db,
        name="Alice Smith",
    )
    first_claim = add_claim(
        db,
        article=first,
        text=first_text,
    )
    second_claim = add_claim(
        db,
        article=second,
        text=second_text,
    )
    first_perspective = add_perspective(
        db,
        article=first,
        claim=first_claim,
        text=first_text,
        entity=entity,
        kind=(
            PerspectiveKind.REPORTED
        ),
        confidence=0.95,
    )
    add_perspective(
        db,
        article=second,
        claim=second_claim,
        text=second_text,
        entity=None,
        kind=(
            PerspectiveKind
            .UNATTRIBUTED
        ),
        confidence=0.7,
    )

    filtered = client.get(
        f"/stories/{story.id}/perspectives",
        params={
            "perspective_kind": (
                "reported"
            ),
            "holder_entity_id": str(
                entity.id
            ),
            "min_confidence": 0.9,
            "source_id": str(
                alpha.id
            ),
        },
    )
    assert filtered.status_code == 200
    assert (
        filtered.json()["total"]
        == 1
    )
    assert (
        filtered.json()["items"][
            0
        ]["id"]
        == str(
            first_perspective.id
        )
    )

    page = client.get(
        f"/stories/{story.id}/perspectives",
        params={
            "page_size": 1,
        },
    )
    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert page.json()["pages"] == 2


def test_missing_perspective_parents_return_404(
    client,
):
    missing = uuid4()

    assert client.get(
        f"/claims/{missing}/perspectives"
    ).status_code == 404
    assert client.get(
        f"/articles/{missing}/perspectives"
    ).status_code == 404
    assert client.get(
        f"/stories/{missing}/perspectives"
    ).status_code == 404
