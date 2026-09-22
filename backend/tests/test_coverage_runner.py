from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select

from app.enums.coverage_scope import CoverageScope
from app.models.coverage import StoryCoverageSummary
from app.models.source import Source
from app.services.coverage import CoverageRunner
from tests.conftest import TestSessionLocal
from tests.coverage_helpers import build_coverage_story


def create_story():
    with TestSessionLocal.begin() as db:
        data = build_coverage_story(db)
        return (
            data["story"].id,
            data["sources"][0].id,
        )


def make_runner(worker_id):
    return CoverageRunner(
        TestSessionLocal,
        worker_id=worker_id,
    )


def test_runner_processes_once_and_reprocesses_coverage_metadata_change():
    story_id, source_id = create_story()
    runner = make_runner("coverage-worker")

    first = runner.run_pending(limit=1)
    assert first.processed == 1

    second = runner.run_pending(limit=1)
    assert second.selected == 0

    with TestSessionLocal.begin() as db:
        source = db.get(
            Source,
            source_id,
        )
        assert source is not None
        source.coverage_scope = (
            CoverageScope.INTERNATIONAL
        )
        source.country = "DE"

    third = runner.run_pending(limit=1)
    assert third.processed == 1

    with TestSessionLocal() as db:
        active = db.scalar(
            select(StoryCoverageSummary)
            .where(
                StoryCoverageSummary.story_id == story_id,
                StoryCoverageSummary.deleted_at.is_(None),
            )
        )
        assert active is not None
        assert (
            active.coverage_scope_counts
            == {"INTERNATIONAL": 1}
        )
        assert active.country_counts == {"DE": 1}


def test_parallel_workers_do_not_duplicate_active_coverage():
    story_ids = []
    with TestSessionLocal.begin() as db:
        for _ in range(4):
            data = build_coverage_story(db)
            story_ids.append(
                data["story"].id
            )

    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        results = list(
            executor.map(
                lambda worker: (
                    make_runner(worker)
                    .run_pending(limit=2)
                ),
                (
                    "coverage-a",
                    "coverage-b",
                ),
            )
        )

    assert sorted(
        result.processed
        for result in results
    ) == [2, 2]

    with TestSessionLocal() as db:
        assert db.scalar(
            select(func.count())
            .select_from(
                StoryCoverageSummary
            )
            .where(
                StoryCoverageSummary
                .story_id.in_(
                    story_ids
                ),
                StoryCoverageSummary
                .deleted_at.is_(None),
            )
        ) == 4
