from datetime import UTC, datetime
import hashlib
from uuid import uuid4

from sqlalchemy import select

from app.analysis.provider import TextPart
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
from app.models.story import (
    Story,
    StoryArticle,
)


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
        source_type=(
            SourceType.NEWS
        ),
    )
    feed = Feed(
        source=source,
        name="Main",
        url=(
            f"https://{slug}.test/feed"
        ),
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
    confidence: float = 0.9,
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
    start = (
        article.normalized_text.index(
            text
        )
    )
    normalized = (
        " ".join(
            text.casefold().split()
        )
    )
    claim = ArticleClaim(
        article_id=article.id,
        processing_run_id=run.id,
        claim_text=text,
        normalized_claim=normalized,
        claim_hash=hashlib.sha256(
            normalized.encode(
                "utf-8"
            )
        ).hexdigest(),
        text_source=TextPart.BODY,
        start_offset=start,
        end_offset=(
            start
            + len(text)
        ),
        sentence_index=0,
        confidence=confidence,
        extraction_provider="test",
        extraction_version="1",
        extracted_at=(
            datetime.now(UTC)
        ),
    )
    db.add(claim)
    db.flush()
    return claim


def add_story_membership(
    db,
    *,
    article,
):
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
        article_time=(
            article.published_at
        ),
        title_terms=[],
        entity_ids=[],
        topic_ids=[],
        similarity_score=0.0,
        match_kind="created",
        match_details=None,
        clustered_at=(
            datetime.now(UTC)
        ),
    )
    db.add(membership)
    db.flush()
    return story


def test_claim_read_endpoints(
    client,
    db,
):
    source, feed = add_source(
        db,
        slug="alpha",
    )
    text = (
        "The government approved the climate package."
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
    story = add_story_membership(
        db,
        article=article,
    )

    article_response = client.get(
        f"/articles/{article.id}/claims"
    )
    assert (
        article_response.status_code
        == 200
    )
    assert [
        item["id"]
        for item
        in article_response.json()
    ] == [
        str(claim.id)
    ]

    detail = client.get(
        f"/claims/{claim.id}"
    )
    assert detail.status_code == 200
    detail_data = detail.json()
    assert (
        detail_data["source_id"]
        == str(source.id)
    )
    assert (
        detail_data["story_id"]
        == str(story.id)
    )

    story_response = client.get(
        f"/stories/{story.id}/claims"
    )
    assert (
        story_response.status_code
        == 200
    )
    assert (
        story_response.json()[
            "total"
        ]
        == 1
    )
    assert (
        story_response.json()[
            "items"
        ][0]["id"]
        == str(claim.id)
    )


def test_claim_reads_hide_soft_deleted_and_ineligible_data(
    client,
    db,
):
    source, feed = add_source(
        db,
        slug="beta",
    )
    text = (
        "The government approved the climate package."
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
    story = add_story_membership(
        db,
        article=article,
    )

    claim.deleted_at = (
        datetime.now(UTC)
    )
    db.flush()

    assert client.get(
        f"/articles/{article.id}/claims"
    ).json() == []
    assert client.get(
        f"/claims/{claim.id}"
    ).status_code == 404
    assert client.get(
        f"/stories/{story.id}/claims"
    ).json()["total"] == 0

    claim.deleted_at = None
    source.active = False
    db.flush()

    assert client.get(
        f"/articles/{article.id}/claims"
    ).status_code == 404
    assert client.get(
        f"/claims/{claim.id}"
    ).status_code == 404
    assert client.get(
        f"/stories/{story.id}/claims"
    ).status_code == 404


def test_story_claim_filters_and_pagination(
    client,
    db,
):
    alpha, alpha_feed = (
        add_source(
            db,
            slug="alpha-filter",
        )
    )
    _, beta_feed = add_source(
        db,
        slug="beta-filter",
    )

    first = add_article(
        db,
        feed=alpha_feed,
        text=(
            "Alpha source published a factual claim today."
        ),
    )
    second = add_article(
        db,
        feed=beta_feed,
        text=(
            "Beta source published another factual claim today."
        ),
    )

    story = add_story_membership(
        db,
        article=first,
    )

    run = add_run(
        db,
        article=second,
        pipeline=(
            ArticlePipeline
            .STORY_CLUSTERING
            .value
        ),
    )
    membership = StoryArticle(
        story_id=story.id,
        article_id=second.id,
        processing_run_id=run.id,
        article_title=second.title,
        article_time=(
            second.published_at
        ),
        title_terms=[],
        entity_ids=[],
        topic_ids=[],
        similarity_score=0.8,
        match_kind="matched",
        match_details=None,
        clustered_at=(
            datetime.now(UTC)
        ),
    )
    db.add(membership)

    first_claim = add_claim(
        db,
        article=first,
        text=(
            "Alpha source published a factual claim today."
        ),
        confidence=0.95,
    )
    add_claim(
        db,
        article=second,
        text=(
            "Beta source published another factual claim today."
        ),
        confidence=0.55,
    )
    db.flush()

    filtered = client.get(
        f"/stories/{story.id}/claims",
        params={
            "min_confidence": 0.9,
            "source_id": str(
                alpha.id
            ),
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0][
        "id"
    ] == str(first_claim.id)

    page = client.get(
        f"/stories/{story.id}/claims",
        params={
            "page_size": 1,
        },
    )
    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert page.json()["pages"] == 2


def test_missing_claim_story_and_article_return_404(
    client,
):
    missing = uuid4()

    assert client.get(
        f"/claims/{missing}"
    ).status_code == 404
    assert client.get(
        f"/articles/{missing}/claims"
    ).status_code == 404
    assert client.get(
        f"/stories/{missing}/claims"
    ).status_code == 404
