from datetime import UTC, datetime
from time import monotonic
from types import SimpleNamespace
from uuid import uuid4

import pytest

from scripts import run_staged_analysis_catchup as job


def test_choose_targets_reserves_newest_and_oldest_without_duplicates():
    newest_first = [uuid4() for _ in range(20)]
    assert job.choose_targets(newest_first, 10) == (
        newest_first[:8] + [newest_first[-1], newest_first[-2]]
    )
    assert job.choose_targets(newest_first, 25) == newest_first
    assert job.choose_targets([], 5) == []
    assert job.choose_targets(newest_first, 1) == newest_first[:1]


def test_choose_targets_rejects_bad_limit_and_duplicates():
    story_id = uuid4()
    with pytest.raises(ValueError, match="positive"):
        job.choose_targets([story_id], 0)
    with pytest.raises(ValueError, match="unique"):
        job.choose_targets([story_id, story_id], 1)


def test_stages_run_sequentially_in_dependency_order(monkeypatch):
    ids = [uuid4() for _ in range(5)]
    stages = []
    labels = [
        "claim_relations", "evidence", "consensus", "coverage"
    ]
    monkeypatch.setattr(job, "build_services", lambda: (1, 2, 3, 4))

    def fake_runner(name):
        class Runner:
            def __init__(self, *_args, target_ids, **_kwargs):
                assert target_ids == ids
                self.cursor = 0

            def run_pending(self, *, limit):
                assert limit == 2
                stages.append(name)
                taken = min(limit, len(ids) - self.cursor)
                self.cursor += taken
                return SimpleNamespace(
                    selected=taken,
                    processed=taken,
                    skipped=0,
                    failed=0,
                )

        return Runner

    for name, attribute in zip(
        labels,
        (
            "TargetedClaimRelations", "TargetedEvidence",
            "TargetedConsensus", "TargetedCoverage",
        ),
    ):
        monkeypatch.setattr(job, attribute, fake_runner(name))
    assert job.execute_stages(ids, monotonic() + 120, 2) == 0
    assert stages == [name for name in labels for _ in range(3)]


def test_failure_stops_before_downstream_stage(monkeypatch):
    ids = [uuid4()]
    calls = []
    monkeypatch.setattr(job, "build_services", lambda: (1, 2, 3, 4))

    class FailingRunner:
        def __init__(self, *_args, target_ids, **_kwargs):
            self.cursor = 0

        def run_pending(self, *, limit):
            calls.append("relations")
            self.cursor += 1
            return SimpleNamespace(
                selected=1, processed=0, skipped=0, failed=1
            )

    class ForbiddenRunner:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("Do not start downstream after failure")

    monkeypatch.setattr(job, "TargetedClaimRelations", FailingRunner)
    monkeypatch.setattr(job, "TargetedEvidence", ForbiddenRunner)
    assert job.execute_stages(ids, monotonic() + 120, 1) == 1
    assert calls == ["relations"]


def test_deadline_defers_work_without_starting_a_stage(monkeypatch):
    ids = [uuid4()]
    monkeypatch.setattr(job, "build_services", lambda: (1, 2, 3, 4))

    class FakeRunner:
        def __init__(self, *_args, **_kwargs):
            self.cursor = 0

        def run_pending(self, *, limit):
            raise AssertionError("Expired budget must not execute work")

    monkeypatch.setattr(job, "TargetedClaimRelations", FakeRunner)
    assert job.execute_stages(ids, monotonic() - 1, 1) == 0


def test_targeted_selection_does_not_skip_claimable_stories():
    from datetime import timedelta

    target_ids = [uuid4() for _ in range(13)]

    class Service:
        def load_snapshot(self, _db, *, story_id):
            return story_id

        def candidate(self, story_id):
            return SimpleNamespace(story_id=story_id)

    class Repository:
        def claim_candidates(
            self, _db, *, candidates, limit, **_kwargs
        ):
            assert len(candidates) <= limit
            return [
                SimpleNamespace(story_id=c.story_id)
                for c in candidates[:limit]
            ]

    runner = job.TargetedMixin(target_ids=target_ids)
    runner.service = Service()
    runner.processing_repository = Repository()
    runner.pipeline = "claim_relations"
    runner.worker_id = "staged-cursor-test"
    runner.claim_ttl_seconds = int(timedelta(minutes=15).total_seconds())

    claimed = []
    while runner.cursor < len(target_ids):
        claimed.extend(
            runner._claim_pending(
                None,
                limit=3,
                now=datetime.now(UTC),
            )
        )

    assert len(claimed) == len(target_ids)
    assert [item.story_id for item in claimed] == target_ids
