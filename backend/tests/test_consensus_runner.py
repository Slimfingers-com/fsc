from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select

from app.enums.source_dependency import SourceRelationKind
from app.models.consensus import StoryConsensusSummary
from app.models.source_dependency import SourceRelation
from app.services.consensus import ConsensusRunner
from tests.conftest import TestSessionLocal
from tests.consensus_helpers import build_consensus_story


def create_story():
    with TestSessionLocal.begin() as db:
        data = build_consensus_story(db)
        return (
            data["story"].id,
            data["sources"][0].id,
            data["sources"][1].id,
        )


def make_runner(worker_id):
    return ConsensusRunner(
        TestSessionLocal,
        worker_id=worker_id,
    )


def test_runner_reprocesses_shared_newsroom_change():
    story_id, first_source_id, second_source_id = create_story()
    runner = make_runner("consensus-worker")

    first = runner.run_pending(limit=1)
    assert first.processed == 1

    second = runner.run_pending(limit=1)
    assert second.selected == 0

    with TestSessionLocal.begin() as db:
        db.add(
            SourceRelation(
                source_id=first_source_id,
                related_source_id=second_source_id,
                relation_kind=SourceRelationKind.SHARED_NEWSROOM,
            )
        )

    third = runner.run_pending(limit=1)
    assert third.processed == 1

    with TestSessionLocal() as db:
        active = db.scalar(
            select(StoryConsensusSummary)
            .where(
                StoryConsensusSummary.story_id == story_id,
                StoryConsensusSummary.deleted_at.is_(None),
            )
        )
        assert active is not None
        assert active.independent_source_count == 1


def test_runner_does_not_reprocess_ownership_only_change():
    _, _, second_source_id = create_story()
    runner = make_runner("consensus-owner-worker")

    first = runner.run_pending(limit=1)
    assert first.processed == 1

    with TestSessionLocal.begin() as db:
        from app.models.source import Source

        source = db.get(Source, second_source_id)
        assert source is not None
        source.ownership = "Owner A"

    second = runner.run_pending(limit=1)
    assert second.selected == 0


def test_parallel_workers_do_not_duplicate_active_consensus():
    story_ids = []
    with TestSessionLocal.begin() as db:
        for _ in range(4):
            data = build_consensus_story(db)
            story_ids.append(data["story"].id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda worker: make_runner(worker).run_pending(limit=2),
                ("consensus-a", "consensus-b"),
            )
        )

    assert sorted(result.processed for result in results) == [2, 2]

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(StoryConsensusSummary)
            .where(
                StoryConsensusSummary.story_id.in_(story_ids),
                StoryConsensusSummary.deleted_at.is_(None),
            )
        ) == 4
