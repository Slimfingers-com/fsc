from concurrent.futures import (
    ThreadPoolExecutor,
)
from datetime import UTC, datetime
import hashlib
from uuid import uuid4

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
    ArticleProcessingState,
)
from app.models.claim import ArticleClaim
from app.models.entity import ArticleEntity, Entity
from app.models.feed import Feed
from app.models.perspective import ArticlePerspective
from app.models.source import Source
from app.perspectives.rule_based import (
    RuleBasedPerspectiveAnalyzer,
)
from app.services.perspective_analysis import (
    PerspectiveAnalysisRunner,
    PerspectiveAnalysisService,
)
from tests.conftest import (
    TestSessionLocal,
)


def create_committed_articles(
    count: int,
):
    token = uuid4().hex
    now = datetime.now(UTC)

    with TestSessionLocal.begin() as db:
        source = Source(
            name=token,
            normalized_name=token,
            slug=token,
            url=(
                f"https://{token}.test"
            ),
            source_type=SourceType.NEWS,
        )
        feed = Feed(
            source=source,
            name="Main",
            url=(
                f"https://{token}.test/feed"
            ),
        )
        alice = Entity(
            canonical_name="Alice Smith",
            normalized_name=(
                f"alice-smith-{token}"
            ),
            entity_type=(
                EntityType.PERSON
            ),
        )
        bob = Entity(
            canonical_name="Bob Jones",
            normalized_name=(
                f"bob-jones-{token}"
            ),
            entity_type=(
                EntityType.PERSON
            ),
        )
        db.add_all(
            [
                alice,
                bob,
            ]
        )
        db.flush()

        articles = []

        for index in range(
            count
        ):
            text = (
                "Alice Smith said climate package "
                f"number {index} will begin Monday while Bob Jones attended."
            )
            article = Article(
                feed=feed,
                identity_type=(
                    ArticleIdentityType
                    .DERIVED
                ),
                identity_key=(
                    f"{index:064d}"
                ),
                normalized_title="Update",
                normalized_text=text,
                language_code="en",
                content_hash=(
                    f"{index + 1:064x}"
                ),
                normalization_version=1,
                normalized_at=now,
            )
            db.add(article)
            db.flush()

            claim_run = (
                ArticleProcessingRun(
                    article_id=(
                        article.id
                    ),
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
                    started_at=now,
                    finished_at=now,
                    outcome="succeeded",
                )
            )
            db.add(claim_run)
            db.flush()

            normalized = (
                text.casefold()
            )
            db.add(
                ArticleClaim(
                    article_id=(
                        article.id
                    ),
                    processing_run_id=(
                        claim_run.id
                    ),
                    claim_text=text,
                    normalized_claim=(
                        normalized
                    ),
                    claim_hash=(
                        hashlib.sha256(
                            normalized.encode(
                                "utf-8"
                            )
                        ).hexdigest()
                    ),
                    text_source=(
                        TextPart.BODY
                    ),
                    start_offset=0,
                    end_offset=len(
                        text
                    ),
                    sentence_index=0,
                    confidence=0.9,
                    extraction_provider=(
                        "test-claim"
                    ),
                    extraction_version="1",
                    extracted_at=now,
                )
            )

            db.add(
                ArticleEntity(
                    article_id=(
                        article.id
                    ),
                    entity_id=alice.id,
                    processing_run_id=None,
                    mention_text=(
                        "Alice Smith"
                    ),
                    normalized_mention=(
                        "alice smith"
                    ),
                    entity_type=(
                        EntityType.PERSON
                    ),
                    text_source=(
                        TextPart.BODY
                    ),
                    start_offset=0,
                    end_offset=len(
                        "Alice Smith"
                    ),
                    sentence_index=0,
                    confidence=0.9,
                    salience=0.9,
                    extraction_provider=(
                        "test-entity"
                    ),
                    extraction_version="1",
                )
            )
            articles.append(
                article
            )

        db.flush()
        return (
            [
                article.id
                for article
                in articles
            ],
            bob.id,
        )


def make_runner(
    worker_id: str,
):
    return PerspectiveAnalysisRunner(
        TestSessionLocal,
        PerspectiveAnalysisService(
            analyzer=(
                RuleBasedPerspectiveAnalyzer()
            )
        ),
        worker_id=worker_id,
    )


class MutatingAnalyzer(
    RuleBasedPerspectiveAnalyzer
):
    provider = "mutating-test"
    version = "1.0.0"

    def __init__(self):
        self.mutated = False

    def analyze(
        self,
        article,
    ):
        result = super().analyze(
            article
        )

        if (
            not self.mutated
            and article.entity_mentions
        ):
            mention_id = (
                article.entity_mentions[
                    0
                ].mention_id
            )

            with TestSessionLocal.begin() as db:
                mention = db.get(
                    ArticleEntity,
                    mention_id,
                )
                assert mention is not None
                mention.confidence = 0.77

            self.mutated = True

        return result


def test_runner_discards_result_when_upstream_input_changes_during_provider():
    article_ids, _ = (
        create_committed_articles(
            1
        )
    )
    analyzer = MutatingAnalyzer()
    runner = PerspectiveAnalysisRunner(
        TestSessionLocal,
        PerspectiveAnalysisService(
            analyzer=analyzer
        ),
        worker_id=(
            "perspective-stale"
        ),
    )

    first = runner.run_pending(
        limit=1
    )

    assert (
        first.selected,
        first.processed,
        first.skipped,
        first.failed,
    ) == (
        1,
        0,
        1,
        0,
    )

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(
                ArticlePerspective
            )
            .where(
                ArticlePerspective.article_id
                == article_ids[0],
                ArticlePerspective.deleted_at
                .is_(None),
            )
        ) == 0

    second = runner.run_pending(
        limit=1
    )

    assert (
        second.selected,
        second.processed,
        second.skipped,
        second.failed,
    ) == (
        1,
        1,
        0,
        0,
    )


def test_runner_processes_once_and_reprocesses_changed_upstream_inputs():
    article_ids, bob_id = (
        create_committed_articles(
            1
        )
    )
    article_id = article_ids[0]
    runner = make_runner(
        "perspective-worker"
    )

    first = runner.run_pending(
        limit=1
    )

    assert (
        first.selected,
        first.processed,
        first.skipped,
        first.failed,
    ) == (
        1,
        1,
        0,
        0,
    )

    second = runner.run_pending(
        limit=1
    )
    assert second.selected == 0

    with TestSessionLocal.begin() as db:
        article = db.get(
            Article,
            article_id,
        )
        assert article is not None
        text = article.normalized_text
        assert text is not None
        start = text.index(
            "Bob Jones"
        )
        db.add(
            ArticleEntity(
                article_id=article.id,
                entity_id=bob_id,
                processing_run_id=None,
                mention_text="Bob Jones",
                normalized_mention=(
                    "bob jones"
                ),
                entity_type=(
                    EntityType.PERSON
                ),
                text_source=(
                    TextPart.BODY
                ),
                start_offset=start,
                end_offset=(
                    start
                    + len("Bob Jones")
                ),
                sentence_index=0,
                confidence=0.85,
                salience=0.5,
                extraction_provider=(
                    "test-entity"
                ),
                extraction_version="1",
            )
        )

    third = runner.run_pending(
        limit=1
    )
    assert third.processed == 1

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(
                ArticlePerspective
            )
            .where(
                ArticlePerspective.article_id
                == article_id
            )
        ) == 2

        assert db.scalar(
            select(func.count())
            .select_from(
                ArticlePerspective
            )
            .where(
                ArticlePerspective.article_id
                == article_id,
                ArticlePerspective.deleted_at
                .is_(None),
            )
        ) == 1

        state = db.scalar(
            select(
                ArticleProcessingState
            ).where(
                ArticleProcessingState.article_id
                == article_id,
                ArticleProcessingState.pipeline
                == ArticlePipeline
                .PERSPECTIVE_ANALYSIS
                .value,
            )
        )
        assert state is not None
        assert state.attempt_count == 2


def test_parallel_workers_do_not_duplicate_active_perspectives():
    article_ids, _ = (
        create_committed_articles(
            6
        )
    )

    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        results = list(
            executor.map(
                lambda worker: (
                    make_runner(
                        worker
                    ).run_pending(
                        limit=3
                    )
                ),
                (
                    "worker-a",
                    "worker-b",
                ),
            )
        )

    assert sorted(
        result.selected
        for result in results
    ) == [3, 3]
    assert sorted(
        result.processed
        for result in results
    ) == [3, 3]

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(
                ArticlePerspective
            )
            .where(
                ArticlePerspective.deleted_at
                .is_(None)
            )
        ) == 6

        processed_article_ids = set(
            db.scalars(
                select(
                    ArticlePerspective.article_id
                ).where(
                    ArticlePerspective.deleted_at
                    .is_(None)
                )
            ).all()
        )
        assert (
            processed_article_ids
            == set(article_ids)
        )

        assert db.scalar(
            select(func.count())
            .select_from(
                ArticleProcessingRun
            )
            .where(
                ArticleProcessingRun.pipeline
                == ArticlePipeline
                .PERSPECTIVE_ANALYSIS
                .value,
                ArticleProcessingRun.outcome
                == "succeeded",
            )
        ) == 6


def test_runner_deactivates_perspectives_when_claims_disappear():
    article_ids, _ = (
        create_committed_articles(
            1
        )
    )
    article_id = article_ids[0]
    runner = make_runner(
        "perspective-cleanup"
    )

    first = runner.run_pending(
        limit=1
    )
    assert first.processed == 1

    with TestSessionLocal.begin() as db:
        claim = db.scalar(
            select(
                ArticleClaim
            ).where(
                ArticleClaim.article_id
                == article_id,
                ArticleClaim.deleted_at
                .is_(None),
            )
        )
        assert claim is not None
        claim.deleted_at = (
            datetime.now(UTC)
        )

    second = runner.run_pending(
        limit=1
    )
    assert second.selected == 0

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(
                ArticlePerspective
            )
            .where(
                ArticlePerspective.article_id
                == article_id,
                ArticlePerspective.deleted_at
                .is_(None),
            )
        ) == 0

        state = db.scalar(
            select(
                ArticleProcessingState
            ).where(
                ArticleProcessingState.article_id
                == article_id,
                ArticleProcessingState.pipeline
                == ArticlePipeline
                .PERSPECTIVE_ANALYSIS
                .value,
            )
        )
        assert state is not None
        assert (
            state.processed_input_hash
            is None
        )
