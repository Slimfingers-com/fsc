from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.analysis.provider import (
    AnalysisResult,
    EntityMentionResult,
    EntityTopicAnalyzer,
    EntityType,
    TextPart,
    TopicResult,
)
from app.analysis.resolver import EntityResolver, TopicResolver
from app.enums.article_identity_type import ArticleIdentityType
from app.enums.article_pipeline import ArticlePipeline
from app.enums.source_type import SourceType
from app.models.article import Article
from app.models.article_processing import (
    ArticleProcessingRun,
    ArticleProcessingState,
)
from app.models.entity import ArticleEntity, Entity, EntityAlias
from app.models.feed import Feed
from app.models.source import Source
from app.models.topic import ArticleTopic, Topic
from app.services.entity_topic_analysis import (
    EntityTopicAnalysisRunner,
    EntityTopicAnalysisService,
)
from tests.conftest import TestSessionLocal


def make_articles(
    db,
    count: int,
) -> list[Article]:
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

    now = datetime.now(UTC)

    articles = [
        Article(
            feed=feed,
            identity_type=ArticleIdentityType.DERIVED,
            identity_key=f"{index:064d}",
            normalized_title=f"Title {index}",
            normalized_text=f"Body {index}",
            language_code="en",
            content_hash=f"{index:064x}",
            normalization_version=1,
            normalized_at=now,
            created_at=(
                now
                + timedelta(
                    microseconds=index
                )
            ),
        )
        for index in range(count)
    ]

    db.add_all(articles)
    db.flush()

    return articles


class EmptyAnalyzer(EntityTopicAnalyzer):
    provider = "claim-test"
    version = "1"

    def analyze(self, article):
        return AnalysisResult(
            (),
            (),
        )


class PoisonAnalyzer(EntityTopicAnalyzer):
    provider = "poison-test"
    version = "1"

    def analyze(self, article):
        raise RuntimeError(
            "poison article"
        )


class ResultAnalyzer(EntityTopicAnalyzer):
    provider = "result-test"
    version = "1"

    def analyze(self, article):
        return AnalysisResult(
            (
                EntityMentionResult(
                    "OpenAI",
                    "OpenAI",
                    EntityType.ORGANIZATION,
                    0.95,
                    0.9,
                    TextPart.TITLE,
                    0,
                    6,
                    0,
                ),
            ),
            (
                TopicResult(
                    "Artificial Intelligence",
                    0.9,
                    0.95,
                ),
            ),
        )


def committed_articles(
    count: int,
) -> tuple[list, object]:
    with TestSessionLocal.begin() as session:
        articles = make_articles(
            session,
            count,
        )

        return (
            [
                article.id
                for article in articles
            ],
            articles[0].feed.source_id,
        )


def cleanup_source(
    source_id,
) -> None:
    with TestSessionLocal.begin() as session:
        article_ids = select(
            Article.id
        ).join(
            Feed
        ).where(
            Feed.source_id == source_id
        )

        session.execute(
            delete(
                ArticleProcessingRun
            ).where(
                ArticleProcessingRun.article_id.in_(
                    article_ids
                )
            )
        )

        session.execute(
            delete(Source).where(
                Source.id == source_id
            )
        )


def test_analysis_hash_tracks_actual_analysis_input():
    service = EntityTopicAnalysisService(
        analyzer=EmptyAnalyzer()
    )

    article = Article(
        id=uuid4(),
        feed_id=uuid4(),
        identity_type=ArticleIdentityType.DERIVED,
        identity_key="a" * 64,
        normalized_title="Title",
        normalized_text="Body",
        language_code="en",
    )

    original = service.analysis_hash(
        article
    )

    article.normalized_text = (
        "Changed body"
    )

    changed_text = service.analysis_hash(
        article
    )

    article.normalized_text = "Body"
    article.language_code = "de"

    changed_language = (
        service.analysis_hash(
            article
        )
    )

    assert len(
        {
            original,
            changed_text,
            changed_language,
        }
    ) == 3


def test_candidate_contains_complete_processing_identity():
    service = EntityTopicAnalysisService(
        analyzer=EmptyAnalyzer(),
        config_version="config-2",
    )

    article = Article(
        id=uuid4(),
        feed_id=uuid4(),
        identity_type=ArticleIdentityType.DERIVED,
        identity_key="b" * 64,
        normalized_title="Title",
        normalized_text="Body",
        language_code="en",
    )

    candidate = service.candidate(
        article
    )

    assert (
        candidate.article_id
        == article.id
    )
    assert (
        candidate.input_hash
        == service.analysis_hash(
            article
        )
    )
    assert (
        candidate.provider
        == EmptyAnalyzer.provider
    )
    assert (
        candidate.provider_version
        == EmptyAnalyzer.version
    )
    assert (
        candidate.configuration_version
        == "config-2"
    )


def test_ambiguous_and_soft_deleted_aliases_are_not_arbitrarily_reused(
    db,
):
    alias = (
        f"shared-{uuid4().hex}"
    )

    entities = [
        Entity(
            canonical_name=(
                f"Entity {index}"
            ),
            normalized_name=(
                f"entity-{uuid4().hex}"
            ),
            entity_type=(
                EntityType.ORGANIZATION
            ),
        )
        for index in range(2)
    ]

    db.add_all(
        entities
    )
    db.flush()

    db.add_all(
        [
            EntityAlias(
                entity_id=entity.id,
                original_alias=alias,
                normalized_alias=alias,
                entity_type=(
                    EntityType.ORGANIZATION
                ),
            )
            for entity in entities
        ]
    )

    db.flush()

    result = EntityMentionResult(
        alias,
        alias,
        EntityType.ORGANIZATION,
        0.99,
        0.9,
        TextPart.BODY,
    )

    assert (
        EntityResolver()
        .resolve(
            db,
            result,
        )
        is None
    )

    entities[1].deleted_at = (
        datetime.now(UTC)
    )

    db.flush()

    assert (
        EntityResolver()
        .resolve(
            db,
            result,
        )
        .id
        == entities[0].id
    )


def _concurrent_resolve(
    kind: str,
) -> list:
    normalized = (
        f"concurrent-{uuid4().hex}"
    )

    barrier = Barrier(2)

    def resolve():
        with TestSessionLocal() as session:
            barrier.wait()

            with session.begin():
                if kind == "entity":
                    value = (
                        EntityResolver()
                        .resolve(
                            session,
                            EntityMentionResult(
                                normalized,
                                normalized,
                                EntityType.ORGANIZATION,
                                0.99,
                                0.9,
                                TextPart.BODY,
                            ),
                        )
                    )

                else:
                    value = (
                        TopicResolver()
                        .resolve(
                            session,
                            TopicResult(
                                normalized,
                                0.9,
                                0.99,
                            ),
                        )
                    )

                return value.id

    with ThreadPoolExecutor(
        max_workers=2
    ) as pool:
        ids = list(
            pool.map(
                lambda _: resolve(),
                range(2),
            )
        )

    with TestSessionLocal.begin() as session:
        if kind == "entity":
            session.execute(
                delete(Entity).where(
                    Entity.id.in_(ids)
                )
            )
        else:
            session.execute(
                delete(Topic).where(
                    Topic.id.in_(ids)
                )
            )

    return ids


@pytest.mark.parametrize(
    "kind",
    [
        "entity",
        "topic",
    ],
)
def test_concurrent_resolution_returns_one_record_without_integrity_error(
    kind,
):
    ids = _concurrent_resolve(
        kind
    )

    assert (
        ids[0]
        == ids[1]
    )


def test_unicode_slug_collisions_do_not_merge_different_topics(
    db,
):
    resolver = TopicResolver()

    first = resolver.resolve(
        db,
        TopicResult(
            "café policy",
            0.9,
            0.99,
        ),
    )

    second = resolver.resolve(
        db,
        TopicResult(
            "cafe policy",
            0.9,
            0.99,
        ),
    )

    assert (
        first.id
        != second.id
    )

    assert (
        first.slug
        != second.slug
    )


def test_offset_constraints_are_database_enforced(
    db,
):
    article = make_articles(
        db,
        1,
    )[0]

    entity = Entity(
        canonical_name="Constraint",
        normalized_name=(
            f"constraint-{uuid4().hex}"
        ),
        entity_type=(
            EntityType.OTHER
        ),
    )

    db.add(
        entity
    )
    db.flush()

    invalid = ArticleEntity(
        article_id=article.id,
        entity_id=entity.id,
        mention_text="x",
        normalized_mention="x",
        entity_type=entity.entity_type,
        text_source=TextPart.BODY,
        start_offset=2,
        end_offset=1,
        confidence=0.9,
        salience=0.9,
        extraction_provider="test",
        extraction_version="1",
    )

    with pytest.raises(
        IntegrityError
    ), db.begin_nested():
        db.add(
            invalid
        )
        db.flush()


def test_two_parallel_workers_process_each_article_once():
    article_ids, source_id = (
        committed_articles(6)
    )

    try:
        runners = [
            EntityTopicAnalysisRunner(
                TestSessionLocal,
                EntityTopicAnalysisService(
                    analyzer=(
                        EmptyAnalyzer()
                    )
                ),
                worker_id=(
                    f"worker-{index}"
                ),
            )
            for index in range(2)
        ]

        with ThreadPoolExecutor(
            max_workers=2
        ) as pool:
            results = list(
                pool.map(
                    lambda runner: (
                        runner.run_pending(
                            limit=6
                        )
                    ),
                    runners,
                )
            )

        assert sum(
            result.selected
            for result in results
        ) == 6

        assert sum(
            result.processed
            for result in results
        ) == 6

        assert sum(
            result.skipped
            for result in results
        ) == 0

        with TestSessionLocal() as session:
            states = list(
                session.scalars(
                    select(
                        ArticleProcessingState
                    ).where(
                        ArticleProcessingState.article_id.in_(
                            article_ids
                        ),
                        ArticleProcessingState.pipeline
                        == ArticlePipeline.ENTITY_TOPIC.value,
                    )
                )
            )

            runs = list(
                session.scalars(
                    select(
                        ArticleProcessingRun
                    ).where(
                        ArticleProcessingRun.article_id.in_(
                            article_ids
                        ),
                        ArticleProcessingRun.pipeline
                        == ArticlePipeline.ENTITY_TOPIC.value,
                    )
                )
            )

            assert (
                len(states)
                == 6
            )

            assert (
                len(runs)
                == 6
            )

            assert all(
                state.processed_provider
                == EmptyAnalyzer.provider
                for state in states
            )

            assert all(
                state.claimed_by is None
                for state in states
            )

            assert all(
                run.outcome
                == "succeeded"
                for run in runs
            )

    finally:
        cleanup_source(
            source_id
        )


def test_parallel_workers_can_process_articles_from_same_feed():
    article_ids, source_id = (
        committed_articles(4)
    )

    barrier = Barrier(2)

    class BarrierAnalyzer(
        EntityTopicAnalyzer
    ):
        provider = (
            "same-feed-test"
        )
        version = "1"

        def analyze(
            self,
            article,
        ):
            barrier.wait()

            return AnalysisResult(
                (),
                (),
            )

    try:
        runners = [
            EntityTopicAnalysisRunner(
                TestSessionLocal,
                EntityTopicAnalysisService(
                    analyzer=(
                        BarrierAnalyzer()
                    )
                ),
                worker_id=(
                    f"worker-{index}"
                ),
            )
            for index in range(2)
        ]

        with ThreadPoolExecutor(
            max_workers=2
        ) as pool:
            results = list(
                pool.map(
                    lambda runner: (
                        runner.run_pending(
                            limit=1
                        )
                    ),
                    runners,
                )
            )

        assert all(
            result.selected == 1
            for result in results
        )

        assert all(
            result.processed == 1
            for result in results
        )

        with TestSessionLocal() as session:
            runs = list(
                session.scalars(
                    select(
                        ArticleProcessingRun
                    ).where(
                        ArticleProcessingRun.article_id.in_(
                            article_ids
                        ),
                        ArticleProcessingRun.pipeline
                        == ArticlePipeline.ENTITY_TOPIC.value,
                    )
                )
            )

            assert (
                len(runs)
                == 2
            )

            assert len(
                {
                    run.article_id
                    for run in runs
                }
            ) == 2

    finally:
        cleanup_source(
            source_id
        )


def test_poison_article_uses_generic_exponential_retry_backoff():
    article_ids, source_id = (
        committed_articles(1)
    )

    moment = [
        datetime.now(UTC)
    ]

    runner = EntityTopicAnalysisRunner(
        TestSessionLocal,
        EntityTopicAnalysisService(
            analyzer=(
                PoisonAnalyzer()
            )
        ),
        worker_id=(
            "poison-worker"
        ),
        retry_base_seconds=10,
        retry_max_seconds=60,
        clock=lambda: moment[0],
    )

    try:
        first = runner.run_pending(
            limit=1
        )

        assert (
            first.selected,
            first.processed,
            first.failed,
        ) == (
            1,
            0,
            1,
        )

        with TestSessionLocal() as session:
            state = session.scalar(
                select(
                    ArticleProcessingState
                ).where(
                    ArticleProcessingState.article_id
                    == article_ids[0],
                    ArticleProcessingState.pipeline
                    == ArticlePipeline.ENTITY_TOPIC.value,
                )
            )

            runs = list(
                session.scalars(
                    select(
                        ArticleProcessingRun
                    )
                    .where(
                        ArticleProcessingRun.article_id
                        == article_ids[0],
                    )
                    .order_by(
                        ArticleProcessingRun.attempt_number
                    )
                )
            )

            assert (
                state.attempt_count
                == 1
            )

            assert (
                state.retry_after
                == moment[0]
                + timedelta(
                    seconds=10
                )
            )

            assert (
                state.claimed_by
                is None
            )

            assert (
                state.last_error_code
                == "RuntimeError"
            )

            assert (
                len(runs)
                == 1
            )

            assert (
                runs[0].outcome
                == "failed"
            )

            assert (
                runs[0].attempt_number
                == 1
            )

        assert (
            runner.run_pending(
                limit=1
            ).selected
            == 0
        )

        moment[0] += timedelta(
            seconds=11
        )

        second = runner.run_pending(
            limit=1
        )

        assert (
            second.failed
            == 1
        )

        with TestSessionLocal() as session:
            state = session.scalar(
                select(
                    ArticleProcessingState
                ).where(
                    ArticleProcessingState.article_id
                    == article_ids[0],
                    ArticleProcessingState.pipeline
                    == ArticlePipeline.ENTITY_TOPIC.value,
                )
            )

            runs = list(
                session.scalars(
                    select(
                        ArticleProcessingRun
                    )
                    .where(
                        ArticleProcessingRun.article_id
                        == article_ids[0],
                    )
                    .order_by(
                        ArticleProcessingRun.attempt_number
                    )
                )
            )

            assert (
                state.attempt_count
                == 2
            )

            assert (
                state.retry_after
                == moment[0]
                + timedelta(
                    seconds=20
                )
            )

            assert (
                len(runs)
                == 2
            )

            assert [
                run.attempt_number
                for run in runs
            ] == [
                1,
                2,
            ]

            assert all(
                run.outcome
                == "failed"
                for run in runs
            )

    finally:
        cleanup_source(
            source_id
        )


def test_entity_topic_results_reference_successful_processing_run():
    article_ids, source_id = (
        committed_articles(1)
    )

    try:
        with TestSessionLocal.begin() as session:
            article = session.get(
                Article,
                article_ids[0],
            )

            article.normalized_title = (
                "OpenAI"
            )
            article.normalized_text = (
                "OpenAI builds systems."
            )
            article.language_code = "en"

        runner = EntityTopicAnalysisRunner(
            TestSessionLocal,
            EntityTopicAnalysisService(
                analyzer=(
                    ResultAnalyzer()
                )
            ),
            worker_id=(
                "result-worker"
            ),
        )

        result = runner.run_pending(
            limit=1
        )

        assert (
            result.processed
            == 1
        )

        with TestSessionLocal() as session:
            run = session.scalar(
                select(
                    ArticleProcessingRun
                ).where(
                    ArticleProcessingRun.article_id
                    == article_ids[0],
                    ArticleProcessingRun.pipeline
                    == ArticlePipeline.ENTITY_TOPIC.value,
                )
            )

            mentions = list(
                session.scalars(
                    select(
                        ArticleEntity
                    ).where(
                        ArticleEntity.article_id
                        == article_ids[0]
                    )
                )
            )

            topics = list(
                session.scalars(
                    select(
                        ArticleTopic
                    ).where(
                        ArticleTopic.article_id
                        == article_ids[0]
                    )
                )
            )

            assert (
                run is not None
            )

            assert (
                run.outcome
                == "succeeded"
            )

            assert mentions
            assert topics

            assert all(
                mention.processing_run_id
                == run.id
                for mention in mentions
            )

            assert all(
                topic.processing_run_id
                == run.id
                for topic in topics
            )

    finally:
        cleanup_source(
            source_id
        )