from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.clustering.provider import (
    StoryCandidate,
    StoryClusterer,
    StoryClusteringInput,
    StoryClusteringResult,
)
from app.clustering.rule_based import RuleBasedStoryClusterer
from app.services.story_clustering import (
    PreparedStoryClustering,
    StoryClusteringService,
)


class StubClusterer(StoryClusterer):
    provider = "test"
    version = "1"

    def __init__(
        self,
        result: StoryClusteringResult,
    ) -> None:
        self.result = result

    def cluster(
        self,
        article: StoryClusteringInput,
        candidates: tuple[StoryCandidate, ...],
    ) -> StoryClusteringResult:
        return self.result


class FakeStoryRepository:
    def __init__(self) -> None:
        self.run_membership = None
        self.active_membership = None
        self.target_story = None

        self.lock_acquired = False
        self.create_story_called = False
        self.replace_membership_called = False
        self.replace_kwargs = None
        self.has_other_memberships = False

    def acquire_clustering_lock(self, db) -> None:
        self.lock_acquired = True

    def get_membership_by_processing_run(
        self,
        db,
        processing_run_id,
    ):
        return self.run_membership

    def get_active_membership(
        self,
        db,
        article_id,
        *,
        for_update=False,
    ):
        return self.active_membership

    def has_other_active_memberships(
        self,
        db,
        *,
        story_id,
        article_id,
    ):
        return self.has_other_memberships

    def deactivate_story_if_orphan(
        self,
        db,
        *,
        story_id,
        now,
    ):
        return True

    def create_story(
        self,
        db,
        *,
        language_code,
    ):
        self.create_story_called = True

        if self.target_story is None:
            self.target_story = SimpleNamespace(
                id=uuid4(),
                language_code=language_code,
            )

        return self.target_story

    def get_story(
        self,
        db,
        story_id,
        *,
        for_update=False,
    ):
        if (
            self.target_story is not None
            and self.target_story.id == story_id
        ):
            return self.target_story

        return None

    def replace_membership(
        self,
        db,
        **kwargs,
    ):
        self.replace_membership_called = True
        self.replace_kwargs = kwargs

        return SimpleNamespace(
            id=uuid4(),
            story_id=kwargs["story_id"],
            match_kind=kwargs["match_kind"],
        )


def make_prepared(
    *,
    candidate_story_id=None,
) -> PreparedStoryClustering:
    article_id = uuid4()
    article_time = datetime(
        2026,
        9,
        19,
        10,
        0,
        tzinfo=UTC,
    )

    article = StoryClusteringInput(
        article_id=article_id,
        language_code="de",
        article_time=article_time,
        title_terms=("bundestag", "berlin"),
        entity_ids=(uuid4(),),
        topic_ids=(uuid4(),),
    )

    candidates = ()

    if candidate_story_id is not None:
        candidates = (
            StoryCandidate(
                story_id=candidate_story_id,
                membership_id=uuid4(),
                article_id=uuid4(),
                article_time=article_time,
                title_terms=("bundestag",),
                entity_ids=(),
                topic_ids=(),
            ),
        )

    return PreparedStoryClustering(
        article_title="Bundestag in Berlin",
        input_hash="prepared-input-hash",
        article=article,
        candidates=candidates,
    )


def make_result(
    *,
    story_id=None,
    similarity_score=0.0,
) -> StoryClusteringResult:
    return StoryClusteringResult(
        story_id=story_id,
        similarity_score=similarity_score,
        matched_membership_id=None,
        matched_article_id=None,
        details={"provider": "test"},
    )


def make_service(
    repository: FakeStoryRepository,
    result: StoryClusteringResult,
) -> StoryClusteringService:
    return StoryClusteringService(
        clusterer=StubClusterer(result),
        repository=repository,
    )


def test_apply_result_is_idempotent_for_same_processing_run():
    repository = FakeStoryRepository()

    existing_story_id = uuid4()
    existing_membership_id = uuid4()

    repository.run_membership = SimpleNamespace(
        id=existing_membership_id,
        story_id=existing_story_id,
        match_kind="created",
    )

    result = make_result()

    service = make_service(
        repository,
        result,
    )

    applied = service.apply_result(
        object(),
        prepared=make_prepared(),
        result=result,
        processing_run_id=uuid4(),
        clustered_at=datetime.now(UTC),
    )

    assert applied.story_id == existing_story_id
    assert applied.membership_id == existing_membership_id
    assert applied.changed is False
    assert applied.match_kind == "created"

    assert repository.lock_acquired is True
    assert repository.create_story_called is False
    assert repository.replace_membership_called is False


def test_apply_result_creates_new_story_when_no_match():
    repository = FakeStoryRepository()
    result = make_result()

    service = make_service(
        repository,
        result,
    )

    processing_run_id = uuid4()

    applied = service.apply_result(
        object(),
        prepared=make_prepared(),
        result=result,
        processing_run_id=processing_run_id,
        clustered_at=datetime.now(UTC),
    )

    assert applied.changed is True
    assert applied.match_kind == "created"

    assert repository.create_story_called is True
    assert repository.replace_membership_called is True

    assert (
        repository.replace_kwargs["processing_run_id"]
        == processing_run_id
    )
    assert repository.replace_kwargs["match_kind"] == "created"


def test_apply_result_retains_singleton_story_when_no_match():
    repository = FakeStoryRepository()

    story_id = uuid4()

    repository.target_story = SimpleNamespace(
        id=story_id,
        language_code="de",
    )
    repository.active_membership = SimpleNamespace(
        id=uuid4(),
        story_id=story_id,
        match_kind="created",
    )

    result = make_result()

    service = make_service(
        repository,
        result,
    )

    applied = service.apply_result(
        object(),
        prepared=make_prepared(),
        result=result,
        processing_run_id=uuid4(),
        clustered_at=datetime.now(UTC),
    )

    assert applied.story_id == story_id
    assert applied.match_kind == "retained"
    assert repository.create_story_called is False
    assert repository.replace_membership_called is True
    assert (
        repository.replace_kwargs["match_kind"]
        == "retained"
    )


def test_apply_result_moves_article_from_multi_member_story_on_no_match():
    repository = FakeStoryRepository()

    old_story_id = uuid4()

    repository.target_story = SimpleNamespace(
        id=old_story_id,
        language_code="de",
    )
    repository.active_membership = SimpleNamespace(
        id=uuid4(),
        story_id=old_story_id,
        match_kind="matched",
    )
    repository.has_other_memberships = True

    result = make_result()

    service = make_service(
        repository,
        result,
    )

    applied = service.apply_result(
        object(),
        prepared=make_prepared(),
        result=result,
        processing_run_id=uuid4(),
        clustered_at=datetime.now(UTC),
    )

    assert applied.story_id != old_story_id
    assert applied.match_kind == "created"
    assert repository.create_story_called is True


def test_apply_result_matches_existing_candidate_story():
    repository = FakeStoryRepository()

    story_id = uuid4()

    repository.target_story = SimpleNamespace(
        id=story_id,
        language_code="de",
    )

    prepared = make_prepared(
        candidate_story_id=story_id,
    )

    result = make_result(
        story_id=story_id,
        similarity_score=0.8,
    )

    service = make_service(
        repository,
        result,
    )

    applied = service.apply_result(
        object(),
        prepared=prepared,
        result=result,
        processing_run_id=uuid4(),
        clustered_at=datetime.now(UTC),
    )

    assert applied.story_id == story_id
    assert applied.changed is True
    assert applied.match_kind == "matched"

    assert repository.create_story_called is False
    assert repository.replace_membership_called is True
    assert repository.replace_kwargs["match_kind"] == "matched"


def test_apply_result_retains_same_story_on_new_processing_run():
    repository = FakeStoryRepository()

    story_id = uuid4()

    repository.target_story = SimpleNamespace(
        id=story_id,
        language_code="de",
    )
    repository.active_membership = SimpleNamespace(
        id=uuid4(),
        story_id=story_id,
        match_kind="matched",
    )

    prepared = make_prepared(
        candidate_story_id=story_id,
    )

    result = make_result(
        story_id=story_id,
        similarity_score=0.9,
    )

    service = make_service(
        repository,
        result,
    )

    applied = service.apply_result(
        object(),
        prepared=prepared,
        result=result,
        processing_run_id=uuid4(),
        clustered_at=datetime.now(UTC),
    )

    assert applied.story_id == story_id
    assert applied.changed is True
    assert applied.match_kind == "retained"

    assert repository.replace_membership_called is True
    assert repository.replace_kwargs["match_kind"] == "retained"


def test_apply_result_rejects_story_outside_candidate_set():
    repository = FakeStoryRepository()

    result = make_result(
        story_id=uuid4(),
        similarity_score=0.8,
    )

    service = make_service(
        repository,
        result,
    )

    with pytest.raises(
        ValueError,
        match="outside the candidate set",
    ):
        service.apply_result(
            object(),
            prepared=make_prepared(),
            result=result,
            processing_run_id=uuid4(),
            clustered_at=datetime.now(UTC),
        )

    assert repository.lock_acquired is False
    assert repository.replace_membership_called is False


def test_apply_result_rejects_language_mismatch():
    repository = FakeStoryRepository()

    story_id = uuid4()

    repository.target_story = SimpleNamespace(
        id=story_id,
        language_code="en",
    )

    prepared = make_prepared(
        candidate_story_id=story_id,
    )

    result = make_result(
        story_id=story_id,
        similarity_score=0.8,
    )

    service = make_service(
        repository,
        result,
    )

    with pytest.raises(
        ValueError,
        match="language does not match",
    ):
        service.apply_result(
            object(),
            prepared=prepared,
            result=result,
            processing_run_id=uuid4(),
            clustered_at=datetime.now(UTC),
        )

    assert repository.replace_membership_called is False


@pytest.mark.parametrize(
    "score",
    [-0.01, 1.01],
)
def test_apply_result_rejects_invalid_similarity_score(
    score,
):
    repository = FakeStoryRepository()

    result = make_result(
        similarity_score=score,
    )

    service = make_service(
        repository,
        result,
    )

    with pytest.raises(
        ValueError,
        match="between zero and one",
    ):
        service.apply_result(
            object(),
            prepared=make_prepared(),
            result=result,
            processing_run_id=uuid4(),
            clustered_at=datetime.now(UTC),
        )

    assert repository.lock_acquired is False

def test_cluster_article_acquires_lock_before_preparing(
    monkeypatch,
):
    repository = FakeStoryRepository()
    result = make_result()
    service = make_service(
        repository,
        result,
    )

    prepared = make_prepared()
    events = []

    def acquire_lock(db):
        events.append("lock")

    def prepare(
        db,
        *,
        article_id,
        window_hours,
        candidate_limit,
    ):
        events.append("prepare")
        return prepared

    def cluster(value):
        events.append("cluster")
        assert value is prepared
        return result

    def apply_locked(
        db,
        *,
        prepared,
        result,
        processing_run_id,
        clustered_at,
    ):
        events.append("apply")
        return SimpleNamespace(
            story_id=uuid4(),
            membership_id=uuid4(),
            changed=True,
            match_kind="created",
        )

    monkeypatch.setattr(
        repository,
        "acquire_clustering_lock",
        acquire_lock,
    )
    monkeypatch.setattr(
        service,
        "prepare",
        prepare,
    )
    monkeypatch.setattr(
        service,
        "cluster",
        cluster,
    )
    monkeypatch.setattr(
        service,
        "_apply_result_locked",
        apply_locked,
    )

    applied = service.cluster_article(
        object(),
        article_id=prepared.article.article_id,
        processing_run_id=uuid4(),
        clustered_at=datetime.now(UTC),
        window_hours=24.0,
        candidate_limit=100,
    )

    assert applied is not None
    assert events == [
        "lock",
        "prepare",
        "cluster",
        "apply",
    ]

def make_processing_article():
    created_at = datetime(
        2026,
        9,
        19,
        10,
        0,
        tzinfo=UTC,
    )

    return SimpleNamespace(
        id=uuid4(),
        title="Bundestag in Berlin",
        normalized_title="bundestag berlin",
        language_code="de",
        published_at=None,
        created_at=created_at,
    )


def test_clustering_hash_tracks_feature_input():
    service = StoryClusteringService(
        clusterer=StubClusterer(
            make_result()
        ),
    )

    article = make_processing_article()
    entity_id = uuid4()
    topic_id = uuid4()

    original = service.clustering_hash(
        article,
        entity_ids=(entity_id,),
        topic_ids=(topic_id,),
    )

    article.normalized_title = (
        "bundestag wahl berlin"
    )

    changed_title = service.clustering_hash(
        article,
        entity_ids=(entity_id,),
        topic_ids=(topic_id,),
    )

    article.normalized_title = (
        "bundestag berlin"
    )

    changed_entities = service.clustering_hash(
        article,
        entity_ids=(uuid4(),),
        topic_ids=(topic_id,),
    )

    changed_topics = service.clustering_hash(
        article,
        entity_ids=(entity_id,),
        topic_ids=(uuid4(),),
    )

    assert len(
        {
            original,
            changed_title,
            changed_entities,
            changed_topics,
        }
    ) == 4


def test_clustering_hash_is_independent_of_feature_order():
    service = StoryClusteringService(
        clusterer=StubClusterer(
            make_result()
        ),
    )

    article = make_processing_article()

    first_entity = uuid4()
    second_entity = uuid4()
    first_topic = uuid4()
    second_topic = uuid4()

    first = service.clustering_hash(
        article,
        entity_ids=(
            first_entity,
            second_entity,
        ),
        topic_ids=(
            first_topic,
            second_topic,
        ),
    )

    second = service.clustering_hash(
        article,
        entity_ids=(
            second_entity,
            first_entity,
        ),
        topic_ids=(
            second_topic,
            first_topic,
        ),
    )

    assert first == second


def test_candidate_contains_complete_processing_identity():
    service = StoryClusteringService(
        clusterer=StubClusterer(
            make_result()
        ),
        config_version="config-2",
    )

    article = make_processing_article()
    entity_ids = (uuid4(),)
    topic_ids = (uuid4(),)

    candidate = service.candidate(
        article,
        entity_ids=entity_ids,
        topic_ids=topic_ids,
        window_hours=48.0,
        candidate_limit=250,
    )

    assert candidate.article_id == article.id
    assert candidate.input_hash == (
        service.clustering_hash(
            article,
            entity_ids=entity_ids,
            topic_ids=topic_ids,
        )
    )
    assert candidate.provider == "test"
    assert candidate.provider_version == "1"
    assert candidate.configuration_version == (
        service.processing_configuration_version(
            window_hours=48.0,
            candidate_limit=250,
        )
    )


def test_processing_configuration_tracks_clustering_settings():
    service = StoryClusteringService(
        clusterer=StubClusterer(
            make_result()
        ),
    )

    original = (
        service.processing_configuration_version(
            window_hours=24.0,
            candidate_limit=100,
        )
    )

    changed_window = (
        service.processing_configuration_version(
            window_hours=48.0,
            candidate_limit=100,
        )
    )

    changed_limit = (
        service.processing_configuration_version(
            window_hours=24.0,
            candidate_limit=200,
        )
    )

    assert len(
        {
            original,
            changed_window,
            changed_limit,
        }
    ) == 3

def test_processing_configuration_tracks_clusterer_configuration():
    first = StoryClusteringService(
        clusterer=RuleBasedStoryClusterer(
            min_similarity=0.45,
        ),
    )

    second = StoryClusteringService(
        clusterer=RuleBasedStoryClusterer(
            min_similarity=0.50,
        ),
    )

    first_version = (
        first.processing_configuration_version(
            window_hours=24.0,
            candidate_limit=100,
        )
    )

    second_version = (
        second.processing_configuration_version(
            window_hours=24.0,
            candidate_limit=100,
        )
    )

    assert first_version != second_version
