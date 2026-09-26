from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.analysis.provider import EntityType, TextPart
from app.core.settings import settings
from app.enums.article_identity_type import (
    ArticleIdentityType,
)
from app.enums.article_pipeline import ArticlePipeline
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.article_processing import (
    ArticleProcessingRun,
)
from app.models.entity import ArticleEntity, Entity
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.models.topic import ArticleTopic, Topic


def add_source(
    db,
    *,
    name,
    slug,
    active=True,
):
    source = Source(
        name=name,
        normalized_name=slug,
        slug=slug,
        url=f"https://{slug}.test",
        source_type=SourceType.NEWS,
        active=active,
    )
    feed = Feed(
        source=source,
        name="Main",
        url=f"https://{slug}.test/feed",
        active=True,
    )
    db.add(source)
    db.flush()
    return source, feed


def add_article(
    db,
    *,
    feed,
    title,
    language,
    published_at,
):
    article = Article(
        feed=feed,
        identity_type=(
            ArticleIdentityType.DERIVED
        ),
        identity_key=uuid4().hex * 2,
        title=title,
        normalized_title=title.casefold(),
        normalized_text=(
            f"Normalized body for {title}"
        ),
        language_code=language,
        content_hash=uuid4().hex * 2,
        normalization_version=1,
        normalized_at=datetime.now(UTC),
        published_at=published_at,
        link=(
            f"https://{feed.source.slug}.test/"
            f"{uuid4().hex}"
        ),
    )
    db.add(article)
    db.flush()
    return article


def add_membership(
    db,
    *,
    story,
    article,
    match_kind="created",
    similarity=0.0,
    match_details=None,
):
    now = datetime.now(UTC)
    run = ArticleProcessingRun(
        article_id=article.id,
        processing_state_id=None,
        pipeline=(
            ArticlePipeline.STORY_CLUSTERING.value
        ),
        input_hash=uuid4().hex * 2,
        provider="test",
        provider_version="1",
        configuration_version="1",
        worker_id="test-worker",
        attempt_number=1,
        started_at=now,
        finished_at=now,
        outcome="succeeded",
    )
    db.add(run)
    db.flush()

    membership = StoryArticle(
        story_id=story.id,
        article_id=article.id,
        processing_run_id=run.id,
        article_title=article.title,
        article_time=(
            article.published_at
            or article.created_at
        ),
        title_terms=[],
        entity_ids=[],
        topic_ids=[],
        similarity_score=similarity,
        match_kind=match_kind,
        match_details=match_details,
        clustered_at=now,
    )
    db.add(membership)
    db.flush()
    return membership


def add_story(
    db,
    *,
    language="de",
):
    story = Story(
        language_code=language,
    )
    db.add(story)
    db.flush()
    return story


def add_entity(
    db,
    *,
    article,
    name="Berlin",
    entity_type=EntityType.LOCATION,
    entity=None,
    normalized_mention=None,
):
    if entity is None:
        entity = Entity(
            canonical_name=name,
            normalized_name=name.casefold(),
            entity_type=entity_type,
        )
        db.add(entity)
        db.flush()
    else:
        name = entity.canonical_name
        entity_type = entity.entity_type

    mention = ArticleEntity(
        article=article,
        entity=entity,
        processing_run_id=None,
        mention_text=name,
        normalized_mention=(
            normalized_mention
            or name.casefold()
        ),
        entity_type=entity_type,
        text_source=TextPart.TITLE,
        start_offset=None,
        end_offset=None,
        sentence_index=None,
        confidence=0.9,
        salience=0.8,
        extraction_provider="test",
        extraction_version="1",
    )
    db.add(mention)
    db.flush()
    return entity


def add_topic(
    db,
    *,
    article,
    name="Politik",
    slug="politik",
    topic=None,
):
    if topic is None:
        topic = Topic(
            name=name,
            normalized_name=name.casefold(),
            slug=slug,
        )
        db.add(topic)
        db.flush()

    relation = ArticleTopic(
        article=article,
        topic=topic,
        processing_run_id=None,
        relevance=0.9,
        confidence=0.9,
        detection_provider="test",
        detection_version="1",
    )
    db.add(relation)
    db.flush()
    return topic


def test_story_list_summary_sort_and_pagination(
    client,
    db,
):
    now = datetime.now(UTC)
    _, alpha_feed = add_source(
        db,
        name="Alpha",
        slug="alpha",
    )
    _, beta_feed = add_source(
        db,
        name="Beta",
        slug="beta",
    )

    older_story = add_story(db)
    older_article = add_article(
        db,
        feed=alpha_feed,
        title="Older story",
        language="de",
        published_at=now - timedelta(days=2),
    )
    add_membership(
        db,
        story=older_story,
        article=older_article,
    )

    recent_story = add_story(db)
    first = add_article(
        db,
        feed=alpha_feed,
        title="First report",
        language="de",
        published_at=now - timedelta(hours=2),
    )
    latest = add_article(
        db,
        feed=beta_feed,
        title="Latest report",
        language="de",
        published_at=now - timedelta(hours=1),
    )
    add_membership(
        db,
        story=recent_story,
        article=first,
    )
    add_membership(
        db,
        story=recent_story,
        article=latest,
        match_kind="matched",
        similarity=0.75,
    )

    response = client.get(
        "/stories",
        params={
            "sort": "newest",
            "page_size": 1,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["pages"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 1

    item = data["items"][0]
    assert item["story_id"] == str(
        recent_story.id
    )
    assert item["title"] == "Latest report"
    assert item["language_code"] == "de"
    assert item["article_count"] == 2
    assert item["source_count"] == 2

    largest = client.get(
        "/stories",
        params={"sort": "largest"},
    )
    assert largest.status_code == 200
    assert largest.json()["items"][0][
        "story_id"
    ] == str(recent_story.id)

    oldest = client.get(
        "/stories",
        params={"sort": "oldest"},
    )
    assert oldest.status_code == 200
    assert oldest.json()["items"][0][
        "story_id"
    ] == str(older_story.id)


def test_story_list_filters(
    client,
    db,
):
    now = datetime.now(UTC)
    alpha, alpha_feed = add_source(
        db,
        name="Alpha",
        slug="alpha",
    )
    _, beta_feed = add_source(
        db,
        name="Beta",
        slug="beta",
    )
    _, gamma_feed = add_source(
        db,
        name="Gamma",
        slug="gamma",
    )

    story = add_story(db, language="de")
    alpha_article = add_article(
        db,
        feed=alpha_feed,
        title="Berlin election",
        language="de",
        published_at=now,
    )
    beta_article = add_article(
        db,
        feed=beta_feed,
        title="Election follow-up",
        language="de",
        published_at=now + timedelta(minutes=5),
    )
    add_membership(
        db,
        story=story,
        article=alpha_article,
    )
    add_membership(
        db,
        story=story,
        article=beta_article,
        match_kind="matched",
        similarity=0.8,
    )

    entity = add_entity(
        db,
        article=alpha_article,
        entity_type=EntityType.LOCATION,
    )
    topic = add_topic(
        db,
        article=alpha_article,
        slug="wahl",
    )

    other_story = add_story(
        db,
        language="en",
    )
    other_article = add_article(
        db,
        feed=gamma_feed,
        title="Other",
        language="en",
        published_at=now - timedelta(days=5),
    )
    add_membership(
        db,
        story=other_story,
        article=other_article,
    )

    filter_sets = [
        {"language": "de"},
        {"source_id": str(alpha.id)},
        {"source": "beta"},
        {"min_articles": 2},
        {"min_sources": 2},
        {"entity_id": str(entity.id)},
        {"entity_type": "location"},
        {"topic_id": str(topic.id)},
        {"topic_slug": "wahl"},
        {
            "published_from": (
                now - timedelta(minutes=1)
            ).isoformat(),
            "published_to": (
                now + timedelta(minutes=1)
            ).isoformat(),
        },
    ]

    for params in filter_sets:
        response = client.get(
            "/stories",
            params=params,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0][
            "story_id"
        ] == str(story.id)


def test_story_combined_membership_filters_require_one_article(
    client,
    db,
):
    now = datetime.now(UTC)
    _, feed = add_source(
        db,
        name="Alpha",
        slug="alpha",
    )
    story = add_story(db)

    first = add_article(
        db,
        feed=feed,
        title="First",
        language="de",
        published_at=now,
    )
    second = add_article(
        db,
        feed=feed,
        title="Second",
        language="de",
        published_at=now + timedelta(minutes=1),
    )
    add_membership(
        db,
        story=story,
        article=first,
    )
    add_membership(
        db,
        story=story,
        article=second,
        match_kind="matched",
        similarity=0.8,
    )

    entity = add_entity(
        db,
        article=first,
        name="Berlin",
    )
    topic = add_topic(
        db,
        article=second,
        name="Politik",
        slug="politik",
    )

    separated = client.get(
        "/stories",
        params={
            "entity_id": str(entity.id),
            "topic_id": str(topic.id),
        },
    )
    assert separated.status_code == 200
    assert separated.json()["total"] == 0

    add_topic(
        db,
        article=first,
        topic=topic,
    )

    combined = client.get(
        "/stories",
        params={
            "entity_id": str(entity.id),
            "topic_id": str(topic.id),
        },
    )
    assert combined.status_code == 200
    assert combined.json()["total"] == 1
    assert combined.json()["items"][0][
        "story_id"
    ] == str(story.id)


def test_story_detail_contains_current_evidence(
    client,
    db,
):
    now = datetime.now(UTC)
    _, alpha_feed = add_source(
        db,
        name="Alpha",
        slug="alpha",
    )
    _, beta_feed = add_source(
        db,
        name="Beta",
        slug="beta",
    )

    story = add_story(db)
    first = add_article(
        db,
        feed=alpha_feed,
        title="Initial report",
        language="de",
        published_at=now - timedelta(hours=1),
    )
    latest = add_article(
        db,
        feed=beta_feed,
        title="Latest report",
        language="de",
        published_at=now,
    )

    add_membership(
        db,
        story=story,
        article=first,
    )
    matched = add_membership(
        db,
        story=story,
        article=latest,
        match_kind="matched",
        similarity=0.72,
        match_details={
            "title_similarity": 0.6,
            "shared_topics": 1,
        },
    )

    entity = add_entity(
        db,
        article=first,
        name="Berlin",
    )
    topic = add_topic(
        db,
        article=first,
        name="Wahl",
        slug="wahl",
    )

    response = client.get(
        f"/stories/{story.id}"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["story_id"] == str(story.id)
    assert data["title"] == "Latest report"
    assert data["article_count"] == 2
    assert data["source_count"] == 2

    assert [
        value["slug"]
        for value in data["sources"]
    ] == ["Alpha".casefold(), "Beta".casefold()]

    assert [
        value["title"]
        for value in data["articles"]
    ] == [
        "Latest report",
        "Initial report",
    ]

    latest_data = data["articles"][0]
    assert latest_data["membership_id"] == str(
        matched.id
    )
    assert latest_data["source_slug"] == "beta"
    assert datetime.fromisoformat(
        latest_data["published_at"]
    ) == latest.published_at
    assert latest_data["match_kind"] == "matched"
    assert latest_data["similarity_score"] == 0.72
    assert latest_data["match_details"][
        "title_similarity"
    ] == 0.6

    assert data["entities"] == [
        {
            "entity_id": str(entity.id),
            "canonical_name": "Berlin",
            "entity_type": "location",
            "article_count": 1,
        }
    ]
    assert data["topics"] == [
        {
            "topic_id": str(topic.id),
            "name": "Wahl",
            "slug": "wahl",
            "article_count": 1,
        }
    ]


def test_story_reads_exclude_ineligible_memberships(
    client,
    db,
):
    now = datetime.now(UTC)
    _, active_feed = add_source(
        db,
        name="Active",
        slug="active",
    )
    inactive_source, inactive_feed = add_source(
        db,
        name="Inactive",
        slug="inactive",
    )

    story = add_story(db)
    active_article = add_article(
        db,
        feed=active_feed,
        title="Visible",
        language="de",
        published_at=now,
    )
    hidden_article = add_article(
        db,
        feed=inactive_feed,
        title="Hidden newer title",
        language="de",
        published_at=now + timedelta(minutes=5),
    )
    add_membership(
        db,
        story=story,
        article=active_article,
    )
    add_membership(
        db,
        story=story,
        article=hidden_article,
        match_kind="matched",
        similarity=0.9,
    )

    inactive_source.active = False
    db.flush()

    listed = client.get("/stories")
    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert item["title"] == "Visible"
    assert item["article_count"] == 1
    assert item["source_count"] == 1

    detail = client.get(
        f"/stories/{story.id}"
    )
    assert detail.status_code == 200
    assert [
        value["title"]
        for value in detail.json()["articles"]
    ] == ["Visible"]


def test_story_with_no_eligible_membership_is_hidden(
    client,
    db,
):
    now = datetime.now(UTC)
    source, feed = add_source(
        db,
        name="Hidden",
        slug="hidden",
    )
    story = add_story(db)
    article = add_article(
        db,
        feed=feed,
        title="Hidden",
        language="de",
        published_at=now,
    )
    add_membership(
        db,
        story=story,
        article=article,
    )
    source.deleted_at = now
    db.flush()

    listed = client.get("/stories")
    assert listed.status_code == 200
    assert listed.json()["total"] == 0

    detail = client.get(
        f"/stories/{story.id}"
    )
    assert detail.status_code == 404
    assert detail.json() == {
        "detail": "Story not found.",
    }


def test_story_detail_ignores_deleted_entity_topic_links(
    client,
    db,
):
    now = datetime.now(UTC)
    _, feed = add_source(
        db,
        name="Alpha",
        slug="alpha",
    )
    story = add_story(db)
    article = add_article(
        db,
        feed=feed,
        title="Story",
        language="de",
        published_at=now,
    )
    add_membership(
        db,
        story=story,
        article=article,
    )

    entity = add_entity(
        db,
        article=article,
    )
    topic = add_topic(
        db,
        article=article,
    )

    article.entity_mentions[0].deleted_at = now
    article.topics[0].deleted_at = now
    db.flush()

    response = client.get(
        f"/stories/{story.id}"
    )
    assert response.status_code == 200
    assert response.json()["entities"] == []
    assert response.json()["topics"] == []

    assert entity.id is not None
    assert topic.id is not None


def test_story_reads_use_current_article_metadata(
    client,
    db,
):
    now = datetime.now(UTC)
    _, feed = add_source(
        db,
        name="Alpha",
        slug="alpha",
    )
    story = add_story(db)
    article = add_article(
        db,
        feed=feed,
        title="Original title",
        language="de",
        published_at=now,
    )
    add_membership(
        db,
        story=story,
        article=article,
    )

    article.title = "Updated title"
    article.normalized_title = "updated title"
    article.published_at = (
        now + timedelta(hours=2)
    )
    db.flush()

    listed = client.get("/stories")
    assert listed.status_code == 200
    assert listed.json()["items"][0][
        "title"
    ] == "Updated title"

    detail = client.get(
        f"/stories/{story.id}"
    )
    assert detail.status_code == 200
    item = detail.json()["articles"][0]
    assert item["title"] == "Updated title"
    assert datetime.fromisoformat(
        item["published_at"]
    ) == article.published_at
    assert datetime.fromisoformat(
        item["article_time"]
    ) == article.published_at

    old_window = client.get(
        "/stories",
        params={
            "published_from": (
                now - timedelta(minutes=1)
            ).isoformat(),
            "published_to": (
                now + timedelta(minutes=1)
            ).isoformat(),
        },
    )
    assert old_window.status_code == 200
    assert old_window.json()["total"] == 0

    current_window = client.get(
        "/stories",
        params={
            "published_from": (
                article.published_at
                - timedelta(minutes=1)
            ).isoformat(),
            "published_to": (
                article.published_at
                + timedelta(minutes=1)
            ).isoformat(),
        },
    )
    assert current_window.status_code == 200
    assert current_window.json()["total"] == 1


def test_story_reads_exclude_other_ineligible_states(
    client,
    db,
):
    now = datetime.now(UTC)

    def create_case(
        slug,
        mutate,
    ):
        source, feed = add_source(
            db,
            name=slug,
            slug=slug,
        )
        story = add_story(db)
        article = add_article(
            db,
            feed=feed,
            title=slug,
            language="de",
            published_at=now,
        )
        membership = add_membership(
            db,
            story=story,
            article=article,
        )
        mutate(
            source,
            feed,
            article,
            story,
            membership,
        )
        return story

    visible_story = create_case(
        "visible-case",
        lambda *_: None,
    )
    hidden_stories = [
        create_case(
            "feed-inactive-case",
            lambda _s, feed, _a, _st, _m: (
                setattr(feed, "active", False)
            ),
        ),
        create_case(
            "article-deleted-case",
            lambda _s, _f, article, _st, _m: (
                setattr(article, "deleted_at", now)
            ),
        ),
        create_case(
            "article-not-normalized-case",
            lambda _s, _f, article, _st, _m: (
                setattr(article, "normalized_at", None)
            ),
        ),
        create_case(
            "membership-deleted-case",
            lambda _s, _f, _a, _st, membership: (
                setattr(membership, "deleted_at", now)
            ),
        ),
        create_case(
            "story-deleted-case",
            lambda _s, _f, _a, story, _m: (
                setattr(story, "deleted_at", now)
            ),
        ),
    ]
    db.flush()

    listed = client.get("/stories")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0][
        "story_id"
    ] == str(visible_story.id)

    for story in hidden_stories:
        detail = client.get(
            f"/stories/{story.id}"
        )
        assert detail.status_code == 404


def test_story_detail_aggregates_distinct_features(
    client,
    db,
):
    now = datetime.now(UTC)
    _, feed = add_source(
        db,
        name="Alpha",
        slug="alpha",
    )
    story = add_story(db)

    first = add_article(
        db,
        feed=feed,
        title="First",
        language="de",
        published_at=now,
    )
    second = add_article(
        db,
        feed=feed,
        title="Second",
        language="de",
        published_at=now + timedelta(minutes=1),
    )
    add_membership(
        db,
        story=story,
        article=first,
    )
    add_membership(
        db,
        story=story,
        article=second,
        match_kind="matched",
        similarity=0.8,
    )

    entity = add_entity(
        db,
        article=first,
        name="Berlin",
    )
    add_entity(
        db,
        article=first,
        entity=entity,
        normalized_mention="berlin-city",
    )
    add_entity(
        db,
        article=second,
        entity=entity,
    )

    topic = add_topic(
        db,
        article=first,
        name="Politik",
        slug="politik",
    )
    add_topic(
        db,
        article=second,
        topic=topic,
    )

    deleted_entity = add_entity(
        db,
        article=first,
        name="Deleted Entity",
    )
    deleted_topic = add_topic(
        db,
        article=first,
        name="Deleted Topic",
        slug="deleted-topic",
    )
    deleted_entity.deleted_at = now
    deleted_topic.deleted_at = now
    db.flush()

    response = client.get(
        f"/stories/{story.id}"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["entities"] == [
        {
            "entity_id": str(entity.id),
            "canonical_name": "Berlin",
            "entity_type": "location",
            "article_count": 2,
        }
    ]
    assert data["topics"] == [
        {
            "topic_id": str(topic.id),
            "name": "Politik",
            "slug": "politik",
            "article_count": 2,
        }
    ]


def test_story_page_size_is_capped(
    client,
    db,
    monkeypatch,
):
    now = datetime.now(UTC)
    _, feed = add_source(
        db,
        name="Alpha",
        slug="alpha",
    )

    for index in range(2):
        story = add_story(db)
        article = add_article(
            db,
            feed=feed,
            title=f"Story {index}",
            language="de",
            published_at=(
                now + timedelta(minutes=index)
            ),
        )
        add_membership(
            db,
            story=story,
            article=article,
        )

    monkeypatch.setattr(
        settings,
        "story_max_page_size",
        1,
    )

    response = client.get(
        "/stories",
        params={"page_size": 100},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page_size"] == 1
    assert data["pages"] == 2
    assert len(data["items"]) == 1


def test_story_api_validation_and_not_found(
    client,
):
    invalid_page = client.get(
        "/stories",
        params={"page": 0},
    )
    assert invalid_page.status_code == 422

    invalid_min = client.get(
        "/stories",
        params={"min_sources": 0},
    )
    assert invalid_min.status_code == 422

    naive_time = client.get(
        "/stories",
        params={
            "published_from": (
                "2026-09-19T00:00:00"
            ),
        },
    )
    assert naive_time.status_code == 422

    invalid_range = client.get(
        "/stories",
        params={
            "published_from": (
                "2026-09-20T00:00:00Z"
            ),
            "published_to": (
                "2026-09-19T00:00:00Z"
            ),
        },
    )
    assert invalid_range.status_code == 422

    missing = client.get(
        f"/stories/{uuid4()}"
    )
    assert missing.status_code == 404


def test_multilingual_story_exposes_and_filters_member_languages(client, db):
    now = datetime.now(UTC)
    _, de_feed = add_source(
        db,
        name="Deutsch",
        slug="de-source",
    )
    _, en_feed = add_source(
        db,
        name="English",
        slug="en-source",
    )
    story = add_story(db, language="mul")
    de_article = add_article(
        db,
        feed=de_feed,
        title="Deutscher Bericht",
        language="de",
        published_at=now,
    )
    en_article = add_article(
        db,
        feed=en_feed,
        title="English report",
        language="en",
        published_at=now + timedelta(minutes=1),
    )
    add_membership(db, story=story, article=de_article)
    add_membership(
        db,
        story=story,
        article=en_article,
        match_kind="matched",
        similarity=0.9,
    )

    detail = client.get(f"/stories/{story.id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["language_code"] == "mul"
    assert payload["language_codes"] == ["de", "en"]
    assert {
        item["language_code"]
        for item in payload["articles"]
    } == {"de", "en"}

    for language in ("de", "en"):
        response = client.get("/stories", params={"language": language})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["story_id"] == str(story.id)

    missing = client.get("/stories", params={"language": "fr"})
    assert missing.status_code == 200
    assert missing.json()["total"] == 0
