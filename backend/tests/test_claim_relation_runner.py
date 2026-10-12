from concurrent.futures import (
    ThreadPoolExecutor,
)
from datetime import UTC, datetime, timedelta
import hashlib
import threading
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import func, select, text

from app.analysis.provider import TextPart
from app.claim_relations.rule_based import (
    RuleBasedClaimRelationAnalyzer,
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
)
from app.models.feed import Feed
from app.models.source import Source
from app.models.story import Story, StoryArticle
from app.models.story_processing import (
    StoryProcessingRun,
    StoryProcessingState,
)
from app.repositories.claim_relation import (
    ClaimRelationRepository,
)
from app.repositories.story import (
    StoryRepository,
)
from app.services.claim_relations import (
    ClaimRelationRunner,
    ClaimRelationService,
)
from tests.conftest import (
    TestSessionLocal,
)


def create_committed_stories(
    count: int,
):
    story_ids = []
    claim_ids = []

    with TestSessionLocal.begin() as db:
        for story_index in range(
            count
        ):
            story = Story(
                language_code="en"
            )
            db.add(story)
            db.flush()

            for article_index in range(2):
                token = (
                    f"{story_index}-"
                    f"{article_index}-"
                    f"{uuid4().hex}"
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
                text = (
                    "The climate plan "
                    f"number {story_index} "
                    "will begin Monday."
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
                    normalized_title="Update",
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

                cluster_run = (
                    ArticleProcessingRun(
                        article_id=(
                            article.id
                        ),
                        processing_state_id=None,
                        pipeline=(
                            ArticlePipeline
                            .STORY_CLUSTERING
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
                        started_at=(
                            datetime.now(UTC)
                        ),
                        finished_at=(
                            datetime.now(UTC)
                        ),
                        outcome="succeeded",
                    )
                )
                db.add(cluster_run)
                db.flush()
                db.add(
                    StoryArticle(
                        story_id=story.id,
                        article_id=article.id,
                        processing_run_id=(
                            cluster_run.id
                        ),
                        article_title="Update",
                        article_time=(
                            article.published_at
                        ),
                        title_terms=[],
                        entity_ids=[],
                        topic_ids=[],
                        similarity_score=(
                            0.0
                            if article_index == 0
                            else 0.9
                        ),
                        match_kind=(
                            "created"
                            if article_index == 0
                            else "matched"
                        ),
                        match_details=None,
                        clustered_at=(
                            datetime.now(UTC)
                        ),
                    )
                )

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
                        provider="test",
                        provider_version="1",
                        configuration_version="1",
                        worker_id="test",
                        attempt_number=1,
                        started_at=(
                            datetime.now(UTC)
                        ),
                        finished_at=(
                            datetime.now(UTC)
                        ),
                        outcome="succeeded",
                    )
                )
                db.add(claim_run)
                db.flush()

                normalized = (
                    text.casefold()
                    .rstrip(".")
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
                    text_source=(
                        TextPart.BODY
                    ),
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
                db.flush()
                claim_ids.append(
                    claim.id
                )

            story_ids.append(
                story.id
            )

    return story_ids, claim_ids


def make_runner(
    worker_id: str,
    analyzer=None,
):
    return ClaimRelationRunner(
        TestSessionLocal,
        ClaimRelationService(
            analyzer=(
                analyzer
                or RuleBasedClaimRelationAnalyzer()
            )
        ),
        worker_id=worker_id,
    )


class MutatingAnalyzer(
    RuleBasedClaimRelationAnalyzer
):
    provider = "mutating-test"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.mutated = False

    def analyze(
        self,
        story,
    ):
        result = super().analyze(
            story
        )

        if (
            not self.mutated
            and story.claims
        ):
            claim_id = (
                story.claims[0].claim_id
            )

            with TestSessionLocal.begin() as db:
                claim = db.get(
                    ArticleClaim,
                    claim_id,
                )
                assert claim is not None
                claim.confidence = 0.77

            self.mutated = True

        return result


def test_runner_discards_stale_provider_result():
    story_ids, _ = (
        create_committed_stories(
            1
        )
    )
    runner = make_runner(
        "stale-worker",
        analyzer=MutatingAnalyzer(),
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
                StoryClaimGroup
            )
            .where(
                StoryClaimGroup.story_id
                == story_ids[0],
                StoryClaimGroup.deleted_at
                .is_(None),
            )
        ) == 0

    second = runner.run_pending(
        limit=1
    )
    assert (
        second.processed
        == 1
    )


def test_runner_processes_once_and_reprocesses_changed_claim():
    story_ids, claim_ids = (
        create_committed_stories(
            1
        )
    )
    story_id = story_ids[0]
    runner = make_runner(
        "claim-relation-worker"
    )

    first = runner.run_pending(
        limit=1
    )
    assert (
        first.processed
        == 1
    )

    second = runner.run_pending(
        limit=1
    )
    assert (
        second.selected
        == 0
    )

    with TestSessionLocal.begin() as db:
        claim = db.get(
            ArticleClaim,
            claim_ids[0],
        )
        assert claim is not None
        claim.confidence = 0.82

    third = runner.run_pending(
        limit=1
    )
    assert (
        third.processed
        == 1
    )

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(
                StoryClaimGroup
            )
            .where(
                StoryClaimGroup.story_id
                == story_id
            )
        ) == 2

        assert db.scalar(
            select(func.count())
            .select_from(
                StoryClaimGroup
            )
            .where(
                StoryClaimGroup.story_id
                == story_id,
                StoryClaimGroup.deleted_at
                .is_(None),
            )
        ) == 1

        state = db.scalar(
            select(
                StoryProcessingState
            ).where(
                StoryProcessingState.story_id
                == story_id,
                StoryProcessingState.pipeline
                == StoryPipeline
                .CLAIM_RELATIONS
                .value,
            )
        )
        assert state is not None
        assert (
            state.attempt_count
            == 2
        )


def test_parallel_workers_do_not_duplicate_active_groups():
    story_ids, _ = (
        create_committed_stories(
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
    ) == [
        3,
        3,
    ]
    assert sorted(
        result.processed
        for result in results
    ) == [
        3,
        3,
    ]

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(
                StoryClaimGroup
            )
            .where(
                StoryClaimGroup.deleted_at
                .is_(None)
            )
        ) == 6

        processed_story_ids = set(
            db.scalars(
                select(
                    StoryClaimGroup.story_id
                ).where(
                    StoryClaimGroup.deleted_at
                    .is_(None)
                )
            ).all()
        )

        assert (
            processed_story_ids
            == set(story_ids)
        )

        assert db.scalar(
            select(func.count())
            .select_from(
                StoryProcessingRun
            )
            .where(
                StoryProcessingRun.pipeline
                == StoryPipeline
                .CLAIM_RELATIONS
                .value,
                StoryProcessingRun.outcome
                == "succeeded",
            )
        ) == 6



def test_runner_deactivates_groups_when_claims_disappear():
    story_ids, claim_ids = (
        create_committed_stories(
            1
        )
    )
    story_id = story_ids[0]
    runner = make_runner(
        "claim-relation-cleanup"
    )

    first = runner.run_pending(
        limit=1
    )
    assert first.processed == 1

    with TestSessionLocal.begin() as db:
        claims = list(
            db.scalars(
                select(
                    ArticleClaim
                ).where(
                    ArticleClaim.id.in_(
                        claim_ids
                    )
                )
            ).all()
        )
        now = datetime.now(UTC)
        for claim in claims:
            claim.deleted_at = now

    second = runner.run_pending(
        limit=1
    )
    assert second.selected == 0

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(
                StoryClaimGroup
            )
            .where(
                StoryClaimGroup.story_id
                == story_id,
                StoryClaimGroup.deleted_at
                .is_(None),
            )
        ) == 0

        state = db.scalar(
            select(
                StoryProcessingState
            ).where(
                StoryProcessingState.story_id
                == story_id,
                StoryProcessingState.pipeline
                == StoryPipeline
                .CLAIM_RELATIONS
                .value,
            )
        )
        assert state is not None
        assert (
            state.processed_input_hash
            is None
        )



def test_claim_relation_finalization_blocks_claim_extraction_article_lock():
    story_ids, claim_ids = (
        create_committed_stories(
            1
        )
    )
    story_id = story_ids[0]

    with TestSessionLocal() as db:
        claim = db.get(
            ArticleClaim,
            claim_ids[0],
        )
        assert claim is not None
        article_id = claim.article_id

    locks_held = threading.Event()
    release_locks = threading.Event()
    extraction_acquired = threading.Event()

    def hold_claim_relation_finalization_locks():
        with TestSessionLocal.begin() as db:
            story_repository = StoryRepository()
            story_repository.acquire_processing_coordination_lock(
                db
            )
            story_repository.acquire_clustering_lock(db)
            snapshot = (
                ClaimRelationService()
                .load_snapshot(
                    db,
                    story_id=story_id,
                    for_update=True,
                    lock_articles=True,
                )
            )
            assert snapshot is not None
            locks_held.set()
            assert release_locks.wait(
                timeout=5
            )

    def acquire_claim_extraction_article_lock():
        assert locks_held.wait(
            timeout=5
        )
        with TestSessionLocal.begin() as db:
            db.scalar(
                select(
                    Article
                )
                .where(
                    Article.id == article_id
                )
                .with_for_update(
                    of=Article
                )
            )
            extraction_acquired.set()

    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        relation_future = executor.submit(
            hold_claim_relation_finalization_locks
        )
        extraction_future = executor.submit(
            acquire_claim_extraction_article_lock
        )

        assert locks_held.wait(
            timeout=5
        )
        assert not extraction_acquired.wait(
            timeout=0.25
        )

        release_locks.set()

        relation_future.result(
            timeout=5
        )
        extraction_future.result(
            timeout=5
        )

    assert extraction_acquired.is_set()


def test_claim_relation_finalization_blocks_story_mutation_lock():
    story_ids, _ = (
        create_committed_stories(
            1
        )
    )
    story_id = story_ids[0]

    locks_held = threading.Event()
    release_locks = threading.Event()
    clustering_acquired = threading.Event()

    def hold_claim_relation_finalization_locks():
        with TestSessionLocal.begin() as db:
            story_repository = StoryRepository()
            story_repository.acquire_processing_coordination_lock(
                db
            )
            story_repository.acquire_clustering_lock(db)
            snapshot = (
                ClaimRelationService()
                .load_snapshot(
                    db,
                    story_id=story_id,
                    for_update=True,
                    lock_articles=True,
                )
            )
            assert snapshot is not None
            locks_held.set()
            assert release_locks.wait(
                timeout=5
            )

    def acquire_story_clustering_locks():
        assert locks_held.wait(
            timeout=5
        )
        with TestSessionLocal.begin() as db:
            story_repository = StoryRepository()
            story_repository.acquire_processing_coordination_lock(
                db
            )
            story_repository.acquire_clustering_lock(db)
            clustering_acquired.set()

    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        relation_future = executor.submit(
            hold_claim_relation_finalization_locks
        )
        clustering_future = executor.submit(
            acquire_story_clustering_locks
        )

        assert locks_held.wait(
            timeout=5
        )
        assert not clustering_acquired.wait(
            timeout=0.25
        )

        release_locks.set()

        relation_future.result(
            timeout=5
        )
        clustering_future.result(
            timeout=5
        )

    assert clustering_acquired.is_set()


def test_claim_relation_story_lock_is_compatible_with_key_share():
    story_ids, _ = create_committed_stories(1)
    story_id = story_ids[0]
    repository = ClaimRelationRepository()

    with TestSessionLocal.begin() as first_db:
        held = first_db.scalar(
            select(Story)
            .where(Story.id == story_id)
            .with_for_update(
                of=Story,
                read=True,
                key_share=True,
            )
        )
        assert held is not None

        with TestSessionLocal.begin() as second_db:
            second_db.execute(
                text("SET LOCAL lock_timeout = '250ms'")
            )
            locked = repository.get_story(
                second_db,
                story_id=story_id,
                for_update=True,
            )

            assert locked is not None
            assert locked.id == story_id


def test_claim_relation_article_lock_is_compatible_with_key_share():
    story_ids, _ = create_committed_stories(1)
    repository = ClaimRelationRepository()

    with TestSessionLocal() as lookup_db:
        article_id = lookup_db.scalar(
            select(StoryArticle.article_id).where(
                StoryArticle.story_id == story_ids[0]
            ).limit(1)
        )
    assert article_id is not None

    with TestSessionLocal.begin() as first_db:
        held = first_db.scalar(
            select(Article)
            .where(Article.id == article_id)
            .with_for_update(
                of=Article,
                read=True,
                key_share=True,
            )
        )
        assert held is not None

        with TestSessionLocal.begin() as second_db:
            second_db.execute(
                text("SET LOCAL lock_timeout = '250ms'")
            )
            repository.lock_articles(
                second_db,
                article_ids=[article_id],
            )


def test_claim_relation_live_selection_is_newest_first():
    story_ids, _ = create_committed_stories(3)
    # A transaction can give all three Stories the same created_at.
    # Newest-first then falls back to UUID ordering, not insert order.
    with TestSessionLocal() as db:
        expected = db.scalar(
            select(Story.id)
            .where(Story.id.in_(story_ids))
            .order_by(Story.created_at.desc(), Story.id.desc())
            .limit(1)
        )
    runner = make_runner("claim-relation-newest-live")
    result = runner.run_pending(limit=1)
    assert (result.selected, result.processed, result.failed) == (1, 1, 0)
    with TestSessionLocal() as db:
        processed = set(
            db.scalars(
                select(StoryProcessingState.story_id).where(
                    StoryProcessingState.pipeline
                    == StoryPipeline.CLAIM_RELATIONS.value,
                    StoryProcessingState.processed_input_hash.is_not(None),
                )
            )
        )
    assert processed == {expected}


def test_claim_relation_current_stories_skip_snapshot_loading(monkeypatch):
    story_ids, _ = create_committed_stories(2)
    runner = make_runner("claim-relation-current-prefilter")
    initial = runner.run_pending(limit=2)
    assert initial.processed == 2

    def no_snapshot_for_current(*args, **kwargs):
        raise AssertionError("current stories should not load claim snapshots")

    monkeypatch.setattr(runner.service, "load_snapshot", no_snapshot_for_current)
    again = runner.run_pending(limit=2)
    assert (again.selected, again.processed, again.failed) == (0, 0, 0)


def test_claim_relation_backfill_is_reserved_alongside_live():
    prior_ids, _ = create_committed_stories(4)
    first = make_runner("claim-relation-initial")
    assert first.run_pending(limit=4).processed == 4
    fresh_ids, _ = create_committed_stories(2)

    class NextVersionAnalyzer(RuleBasedClaimRelationAnalyzer):
        version = "prefilter-next-version"

    runner = make_runner(
        "claim-relation-priority",
        analyzer=NextVersionAnalyzer(),
    )
    result = runner.run_pending(limit=5)
    assert (result.selected, result.processed, result.failed) == (5, 5, 0)
    with TestSessionLocal() as db:
        changed = set(
            db.scalars(
                select(StoryProcessingState.story_id).where(
                    StoryProcessingState.pipeline
                    == StoryPipeline.CLAIM_RELATIONS.value,
                    StoryProcessingState.processed_provider_version
                    == "prefilter-next-version",
                )
            )
        )
    assert set(fresh_ids).issubset(changed)
    assert len(changed.intersection(prior_ids)) == 3


def test_stale_claim_relation_scan_is_bounded_and_resumes(monkeypatch):
    now = datetime.now(UTC)
    stories = [
        SimpleNamespace(
            id=uuid4(),
            created_at=now + timedelta(seconds=index),
        )
        for index in range(145)
    ]
    runner = make_runner("bounded-stale-claim-relation")
    scanned = []
    pages = []

    def list_candidates(
        _db, *, processed, after_created_at, after_id, limit, **_kwargs
    ):
        assert processed is True
        assert limit == 16
        pages.append((after_created_at, after_id))
        if after_created_at is None:
            start = 0
        else:
            start = next(
                idx + 1
                for idx, story in enumerate(stories)
                if story.id == after_id
            )
        return stories[start:start + limit]

    def snapshot(_db, *, story_id):
        scanned.append(story_id)
        return story_id

    monkeypatch.setattr(
        runner.service.repository, "list_candidate_stories", list_candidates
    )
    monkeypatch.setattr(runner.service, "load_snapshot", snapshot)
    monkeypatch.setattr(
        runner.service, "candidate", lambda story_id: story_id,
    )
    # All are false-positive stale candidates; the existing atomic gate
    # correctly rejects their unchanged input hashes.
    monkeypatch.setattr(
        runner.processing_repository,
        "claim_candidates",
        lambda *_args, **_kwargs: [],
    )

    assert runner._claim_pending_pool(
        None, limit=1, now=now, processed=True,
    ) == []
    assert len(pages) == 8
    assert len(scanned) == 128
    assert runner._stale_scan_cursor is not None

    assert runner._claim_pending_pool(
        None, limit=1, now=now, processed=True,
    ) == []
    assert len(scanned) == 145
    assert scanned == [item.id for item in stories]
    assert runner._stale_scan_cursor is None
